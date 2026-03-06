"""Purpose: Expose admin-only operational and analytics routes.
Responsibilities: Provide usage visibility and system-health endpoints for administrators.
Scope: Admin HTTP endpoints mounted under the main FastAPI app.
Usage: Imported by `app.main` and composed with admin sub-routers.
Invariants/Assumptions: Admin routes should expose operational data and usage workflows for administrators.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from ...database import get_db
from ...models.usage import Usage
from ...models.user import User
from ...schemas.response_schema import ApiResponse
from ...services.security import get_current_user
from ...utils.decorators import require_auth
from ...utils.enums import ResponseStatus
from ...utils.response_utils import create_response
from ...utils.route_helpers import common_responses, handle_route_errors
from .health import router as health_router
from .usage import router as usage_router

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Admin"])


@router.get(
    "/get-usage",
    operation_id="get_admin_usage",
    response_model=ApiResponse[list[dict]],
    responses={403: {"description": "Not authorized"}, **common_responses},
)
@require_auth
@handle_route_errors
async def get_usage(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Return a list of usage stats (per user + usage_type).
    Includes the user's email & display name for better tracking.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view usage stats",
        )

    # Grab usage data + user
    # We can use joinedload if we want eager loading, but let's do a manual join for clarity
    # That means we might do two queries, or a single joined query.
    # Let's do a single joined approach.
    # We'll do joinedload(Usage.user) to get the user
    usage_results = await db.execute(
        select(Usage)
        .where(Usage.deleted_at.is_(None))
        .options(joinedload(Usage.user))
        .order_by(Usage.user_id)
    )
    usage_list = usage_results.scalars().all()

    usage_data = []
    for usage in usage_list:
        # usage.user might be None if there's an orphaned row, but that shouldn't happen
        user_obj = usage.user
        usage_data.append(
            {
                "usage_id": usage.id,
                "user_id": usage.user_id,
                "user_email": user_obj.email if user_obj else None,
                "display_name": user_obj.display_name if user_obj else None,
                "usage_type": usage.usage_type,
                "usage_calls": usage.usage_calls,  # usage_count
                "usage_points": usage.usage_points,  # usage_credits
                "last_used_at": usage.last_used_at,
                "created_at": usage.created_at,
                "updated_at": usage.updated_at,
            }
        )

    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Usage stats retrieved",
        data=usage_data,
    )


__all__ = ["router", "usage_router", "health_router"]
