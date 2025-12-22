"""Shared dependencies for content routes."""

import logging
from typing import Annotated

from fastapi import Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...database import get_db
from ...models.content import Content
from ...models.user import User
from ...services.security import get_current_user
from ...utils.error_handlers import ApplicationException

logger = logging.getLogger(__name__)

# Type aliases for cleaner signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_user_content(
    content_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> Content:
    """
    Dependency that fetches and validates content ownership.
    Raises 404 if content not found or not owned by user.
    """
    query = (
        select(Content)
        .options(
            selectinload(Content.user),
            selectinload(Content.template),
            selectinload(Content.tags),
        )
        .where(
            Content.id == content_id,
            Content.user_id == current_user.id,
            Content.deleted_at.is_(None),
        )
    )
    result = await db.execute(query)
    content = result.scalar_one_or_none()

    if not content:
        raise ApplicationException(
            message="Content not found or unauthorized",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return content


# Dependency for routes that need content validation
ValidatedContent = Annotated[Content, Depends(get_user_content)]
