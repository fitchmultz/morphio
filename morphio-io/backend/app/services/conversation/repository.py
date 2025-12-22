"""Database operations for conversation entities."""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...models.content import Content
from ...models.conversation import ContentConversation, ConversationMessage
from ...utils.error_handlers import ApplicationException
from .context import ConversationContext

logger = logging.getLogger(__name__)

HISTORY_LIMIT = 12


async def get_content_for_user(db: AsyncSession, content_id: int, user_id: int) -> Content:
    """Fetch content by ID with ownership verification.

    Args:
        db: Database session
        content_id: ID of the content to fetch
        user_id: ID of the user requesting the content

    Returns:
        Content object if found and owned by user

    Raises:
        ApplicationException: If content not found or user not authorized
    """
    stmt: Select[tuple[Content]] = (
        select(Content)
        .where(Content.id == content_id, Content.user_id == user_id, Content.deleted_at.is_(None))
        .options(selectinload(Content.template), selectinload(Content.tags))
    )
    result = await db.execute(stmt)
    content = result.scalars().unique().one_or_none()
    if not content:
        raise ApplicationException("Content not found or unauthorized", status_code=404)
    return content


async def get_conversation_for_user(
    db: AsyncSession,
    conversation_id: str,
    user_id: int,
    content_id: int,
) -> ContentConversation:
    """Fetch conversation by ID with ownership verification.

    Args:
        db: Database session
        conversation_id: ID of the conversation to fetch
        user_id: ID of the user requesting the conversation
        content_id: ID of the content the conversation belongs to

    Returns:
        ContentConversation object if found and owned by user

    Raises:
        ApplicationException: If conversation not found
    """
    stmt: Select[tuple[ContentConversation]] = (
        select(ContentConversation)
        .where(
            ContentConversation.id == conversation_id,
            ContentConversation.user_id == user_id,
            ContentConversation.content_id == content_id,
            ContentConversation.deleted_at.is_(None),
        )
        .options(selectinload(ContentConversation.messages))
    )
    result = await db.execute(stmt)
    conversation = result.scalars().unique().one_or_none()
    if not conversation:
        raise ApplicationException("Conversation not found", status_code=404)
    return conversation


async def create_conversation(
    db: AsyncSession,
    *,
    content: Content,
    user_id: int,
    model_choice: str,
    branch_parent_id: Optional[str] = None,
) -> ContentConversation:
    """Create a new conversation for content.

    Args:
        db: Database session
        content: Content object to create conversation for
        user_id: ID of the user creating the conversation
        model_choice: Model to use for the conversation
        branch_parent_id: Optional parent conversation ID for branching

    Returns:
        Newly created ContentConversation object
    """
    context = ConversationContext(
        base_template=(content.template.template_content if content.template else None),
        template_name=(content.template.name if content.template else None),
    )
    conversation = ContentConversation(
        content_id=content.id,
        user_id=user_id,
        template_id=content.template.id if content.template else None,
        template_used=content.template.name if content.template else None,
        model=model_choice,
        context_snapshot=context.to_dict(),
        parent_id=branch_parent_id,
        original_transcript=None,
    )
    db.add(conversation)
    await db.flush()
    logger.info(
        "Created new conversation %s for content %s (user %s)",
        conversation.id,
        content.id,
        user_id,
    )
    return conversation


async def fetch_recent_messages(
    db: AsyncSession, conversation_id: str, limit: int = HISTORY_LIMIT
) -> List[ConversationMessage]:
    """Fetch recent messages for a conversation.

    Args:
        db: Database session
        conversation_id: ID of the conversation
        limit: Maximum number of messages to fetch (default: 12)

    Returns:
        List of ConversationMessage objects, oldest first
    """
    stmt: Select[tuple[ConversationMessage]] = (
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    items = list(result.scalars().all())
    items.reverse()
    return items
