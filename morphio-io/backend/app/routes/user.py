import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select

from ..config import settings
from ..dependencies import CurrentUser, DbSession
from ..models.quota_tier import QuotaTierAssignment
from ..models.usage import Usage
from ..schemas.response_schema import ApiResponse
from ..schemas.user_schema import UserCredits, UserOut, UserUpdate
from ..utils.enums import UserRole
from ..utils.response_utils import utc_now
from ..services.usage import get_current_period_usage_credits
from ..services.security.protection import rate_limit_by_ip
from ..utils.response_utils import ResponseStatus, create_response
from ..utils.route_helpers import common_responses, handle_route_errors

logger = logging.getLogger(__name__)


async def apply_rate_limit(request: Request):
    """Rate limit dependency for user routes."""
    await rate_limit_by_ip(
        request,
        limit=settings.USER_ROUTES_RATE_LIMIT,
        window=settings.USER_ROUTES_RATE_WINDOW,
    )


router = APIRouter(tags=["User"], dependencies=[Depends(apply_rate_limit)])


@router.get(
    "/profile",
    operation_id="get_user_profile",
    response_model=ApiResponse[UserOut],
    responses={**common_responses},
)
@handle_route_errors
async def get_user_profile(current_user: CurrentUser):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user_out = UserOut.model_validate(current_user)
    return create_response(
        status=ResponseStatus.SUCCESS,
        message="User profile retrieved successfully",
        data=user_out.model_dump(),
    )


@router.post(
    "/change-display-name",
    operation_id="change_display_name",
    response_model=ApiResponse[UserOut],
    responses={**common_responses},
)
@handle_route_errors
async def change_display_name(
    update_data: UserUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    if update_data.display_name is None:
        raise HTTPException(status_code=400, detail="New display name is required")
    current_user.display_name = str(update_data.display_name)
    await db.commit()
    await db.refresh(current_user)
    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Display name updated successfully",
        data=UserOut.model_validate(current_user).model_dump(),
    )


@router.post(
    "/change-email",
    operation_id="change_email",
    response_model=ApiResponse[UserOut],
    responses={**common_responses},
)
@handle_route_errors
async def change_email(
    update_data: UserUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    if update_data.email is None:
        raise HTTPException(status_code=400, detail="New email is required")
    current_user.email = str(update_data.email)
    await db.commit()
    await db.refresh(current_user)
    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Email updated successfully",
        data=UserOut.model_validate(current_user).model_dump(),
    )


@router.get(
    "/credits",
    operation_id="get_user_credits",
    response_model=ApiResponse[UserCredits],
    responses={
        **common_responses,
        200: {
            "description": "User credits retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "User credits retrieved successfully",
                        "data": {
                            "tier": "free",
                            "limit": 50,
                            "used": 12,
                            "remaining": 38,
                            "remaining_pct": 76.0,
                            "reset_date": "2025-02-01",
                            "resets_monthly": True,
                            "is_admin": False,
                        },
                    }
                }
            },
        },
        401: {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "message": "Not authenticated",
                        "data": {"error_type": "HTTPException", "details": {}},
                    }
                }
            },
        },
    },
)
@handle_route_errors
async def get_user_credits(
    current_user: CurrentUser,
    db: DbSession,
):
    """Get summary of a user's credit usage for the current monthly period."""
    # Determine effective quota tier
    quota_tier = "free"
    quota_tier_result = await db.execute(
        select(QuotaTierAssignment).where(
            QuotaTierAssignment.user_id == current_user.id,
            QuotaTierAssignment.deleted_at.is_(None),
        )
    )
    quota_assignments = quota_tier_result.scalars().all()
    active_tier = next((record for record in quota_assignments if record.status == "active"), None)
    if active_tier:
        quota_tier = active_tier.tier.lower()

    tier_limit = settings.QUOTA_TIER_LIMITS.get(quota_tier, 50)
    is_admin = current_user.role == UserRole.ADMIN

    now = utc_now()
    total_used = await get_current_period_usage_credits(db, current_user.id, now=now)

    # Admins have unlimited credits
    if is_admin:
        remaining = 999999999
        tier_limit = 999999999
        remaining_pct = 100.0
    else:
        remaining = max(0, tier_limit - total_used)
        remaining_pct = (remaining / tier_limit * 100) if tier_limit > 0 else 0.0

    # Calculate reset date (first of next month)
    next_month = now.month % 12 + 1
    next_year = now.year if now.month < 12 else now.year + 1
    reset_date = f"{next_year:04d}-{next_month:02d}-01"

    credits_data = UserCredits(
        tier=quota_tier,
        limit=tier_limit,
        used=total_used,
        remaining=remaining,
        remaining_pct=round(remaining_pct, 1),
        reset_date=reset_date,
        resets_monthly=True,
        is_admin=is_admin,
    )

    return create_response(
        status=ResponseStatus.SUCCESS,
        message="User credits retrieved successfully",
        data=credits_data.model_dump(),
    )


@router.get(
    "/usage",
    operation_id="get_user_usage",
    response_model=ApiResponse[list[dict]],
    responses={**common_responses},
)
@handle_route_errors
async def get_current_user_usage(
    current_user: CurrentUser,
    db: DbSession,
):
    results = await db.execute(
        select(Usage).where(Usage.user_id == current_user.id, Usage.deleted_at.is_(None))
    )
    usage_list = results.scalars().all()

    usage_data = []
    for usage_item in usage_list:
        usage_data.append(
            {
                "usage_type": usage_item.usage_type,
                "usage_count": usage_item.usage_count,
                "usage_credits": usage_item.usage_credits,
                "last_used_at": (
                    usage_item.last_used_at.isoformat() if usage_item.last_used_at else None
                ),
                "created_at": (
                    usage_item.created_at.isoformat() if usage_item.created_at else None
                ),
                "updated_at": (
                    usage_item.updated_at.isoformat() if usage_item.updated_at else None
                ),
            }
        )

    return create_response(
        status=ResponseStatus.SUCCESS,
        message="User usage retrieved successfully",
        data=usage_data,
    )
