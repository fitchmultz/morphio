import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..models.usage import Usage
from ..models.user import User
from ..schemas.user_schema import UserOut, UserUpdate
from ..services.security import get_current_user
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
    response_model=UserOut,
    responses={**common_responses},
)
@handle_route_errors
async def get_user_profile(current_user: User = Depends(get_current_user)):
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
    response_model=UserOut,
    responses={**common_responses},
)
@handle_route_errors
async def change_display_name(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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
    response_model=UserOut,
    responses={**common_responses},
)
@handle_route_errors
async def change_email(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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
    "/usage",
    operation_id="get_user_usage",
    responses={**common_responses},
)
@handle_route_errors
async def get_current_user_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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
