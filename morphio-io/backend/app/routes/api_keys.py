"""API key management endpoints."""

import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.api_key import APIKey
from ..models.user import User
from ..services.security import get_current_user
from ..utils.decorators import require_auth
from ..utils.enums import ResponseStatus
from ..utils.response_utils import create_response
from ..utils.route_helpers import common_responses, handle_route_errors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user/api-keys", tags=["API Keys"])


class APIKeyCreate(BaseModel):
    """Request body for creating an API key."""

    name: str = Field(..., min_length=1, max_length=100, description="Friendly name for the key")
    scopes: list[str] | None = Field(default=None, description="Optional list of permission scopes")


class APIKeyOut(BaseModel):
    """API key response (without the actual key)."""

    model_config = {"from_attributes": True}

    id: int
    name: str
    key_prefix: str
    scopes: list[str]
    last_used_at: datetime | None
    created_at: datetime


class APIKeyCreatedOut(APIKeyOut):
    """API key response with the plaintext key (only returned on creation)."""

    key: str = Field(..., description="The API key. Store this securely - it won't be shown again!")


@router.post(
    "",
    operation_id="create_api_key",
    responses={
        200: {"description": "API key created successfully"},
        400: {"description": "Invalid request"},
        **common_responses,
    },
)
@require_auth
@handle_route_errors
async def create_api_key(
    body: APIKeyCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new API key for the current user.

    The plaintext key is only returned once at creation time.
    Store it securely - it cannot be retrieved later.
    """
    # Check for duplicate name
    existing = await db.execute(
        select(APIKey).where(
            APIKey.user_id == current_user.id,
            APIKey.name == body.name,
            APIKey.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An API key with name '{body.name}' already exists",
        )

    # Create the key
    api_key, plaintext_key = APIKey.create_key(
        user_id=current_user.id,
        name=body.name,
        scopes=body.scopes,
    )

    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    logger.info(f"API key created for user {current_user.id}: {api_key.key_prefix}...")

    return create_response(
        status=ResponseStatus.SUCCESS,
        message="API key created successfully. Store it securely - it won't be shown again!",
        data=APIKeyCreatedOut(
            id=api_key.id,
            name=api_key.name,
            key_prefix=api_key.key_prefix,
            scopes=api_key.get_scopes(),
            last_used_at=api_key.last_used_at,
            created_at=api_key.created_at,
            key=plaintext_key,
        ).model_dump(),
    )


@router.get(
    "",
    operation_id="list_api_keys",
    responses={
        200: {"description": "List of API keys"},
        **common_responses,
    },
)
@require_auth
@handle_route_errors
async def list_api_keys(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    List all API keys for the current user.

    The plaintext key is not returned - only the prefix for identification.
    """
    result = await db.execute(
        select(APIKey)
        .where(
            APIKey.user_id == current_user.id,
            APIKey.deleted_at.is_(None),
        )
        .order_by(APIKey.created_at.desc())
    )
    keys = result.scalars().all()

    keys_out = [
        APIKeyOut(
            id=key.id,
            name=key.name,
            key_prefix=key.key_prefix,
            scopes=key.get_scopes(),
            last_used_at=key.last_used_at,
            created_at=key.created_at,
        ).model_dump()
        for key in keys
    ]

    return create_response(
        status=ResponseStatus.SUCCESS,
        message=f"Found {len(keys_out)} API key(s)",
        data=keys_out,
    )


@router.delete(
    "/{key_id}",
    operation_id="revoke_api_key",
    responses={
        200: {"description": "API key revoked"},
        404: {"description": "API key not found"},
        **common_responses,
    },
)
@require_auth
@handle_route_errors
async def revoke_api_key(
    key_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Revoke (delete) an API key.

    The key will immediately stop working for authentication.
    """
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == current_user.id,
            APIKey.deleted_at.is_(None),
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    api_key.soft_delete()
    await db.commit()

    logger.info(f"API key revoked for user {current_user.id}: {api_key.key_prefix}...")

    return create_response(
        status=ResponseStatus.SUCCESS,
        message="API key revoked successfully",
        data={"id": key_id},
    )
