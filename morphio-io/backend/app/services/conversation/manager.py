"""Conversation management orchestration."""

from __future__ import annotations

import logging
from typing import List

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...config import settings
from ...models.conversation import ContentConversation, ConversationMessage
from ...schemas.conversation_schema import (
    ConversationMessageOut,
    ConversationRequest,
    ConversationResponse,
    ConversationSummary,
    ConversationThreadOut,
)
from ...services.generation import generate_conversation_completion
from .context import ConversationContext
from .repository import (
    create_conversation,
    fetch_recent_messages,
    get_content_for_user,
    get_conversation_for_user,
)
from .response_parser import parse_model_response, render_assistant_message
from .suggestions import generate_follow_up_suggestions

logger = logging.getLogger(__name__)


async def continue_content_conversation(
    db: AsyncSession,
    *,
    content_id: int,
    user_id: int,
    request: ConversationRequest,
) -> ConversationResponse:
    """Continue or create a content conversation.

    Args:
        db: Database session
        content_id: ID of the content to converse about
        user_id: ID of the user
        request: Conversation request with message and options

    Returns:
        ConversationResponse with updated content and messages
    """
    content = await get_content_for_user(db, content_id, user_id)

    try:
        default_model = request.model or settings.CONTENT_MODEL

        conversation: ContentConversation
        created_new_conversation = False

        if request.branch_from_id:
            parent = await get_conversation_for_user(
                db, request.branch_from_id, user_id, content.id
            )
            model_used = request.model or parent.model or settings.CONTENT_MODEL
            conversation = await create_conversation(
                db,
                content=content,
                user_id=user_id,
                model_choice=model_used,
                branch_parent_id=parent.id,
            )
            parent.log_branch_creation(conversation.id)
            created_new_conversation = True
        elif request.conversation_id and request.preserve_context:
            conversation = await get_conversation_for_user(
                db, request.conversation_id, user_id, content.id
            )
            model_used = request.model or conversation.model or settings.CONTENT_MODEL
            if conversation.model != model_used:
                conversation.model = model_used
        else:
            model_used = default_model
            conversation = await create_conversation(
                db,
                content=content,
                user_id=user_id,
                model_choice=model_used,
                branch_parent_id=None,
            )
            created_new_conversation = True

        conversation.model = model_used

        context = ConversationContext.from_dict(conversation.context_snapshot)
        context.record_user_direction(request.message)

        user_message = ConversationMessage(
            conversation_id=conversation.id,
            role="user",
            content=request.message.strip(),
        )
        db.add(user_message)
        await db.flush()

        history = await fetch_recent_messages(db, conversation.id)
        context_prompt = context.build_prompt(request.message, content.content)

        developer_prompt = (
            "You are an expert content editor collaborating with the user to iteratively improve "
            "content. Always return valid JSON matching this schema: \n"
            "{\n"
            '  "updated_content": string,\n'
            '  "change_summary": array of strings (max 5 entries),\n'
            '  "notes": string or null\n'
            "}.\n"
            "Do not return code fences or additional commentary. The `updated_content` field must "
            "contain the fully updated markdown content that satisfies the user's latest request."
            " Summarize key edits inside `change_summary` in concise bullet-style phrases."
        )

        llm_messages = [
            {"role": "developer", "content": developer_prompt + "\n\nContext:\n" + context_prompt}
        ]
        for msg in history:
            llm_messages.append({"role": msg.role, "content": msg.content})

        raw_response, resolved_model = await generate_conversation_completion(
            llm_messages, chosen_model=model_used
        )
        updated_content, change_summary, notes = parse_model_response(
            raw_response, original_content=content.content
        )
        rendered_assistant_content = render_assistant_message(
            updated_content, change_summary, notes
        )

        # Ensure assistant message is never empty
        if not rendered_assistant_content.strip():
            logger.warning("Assistant message would be empty; using fallback")
            rendered_assistant_content = "I apologize, but I couldn't generate a response. Please try rephrasing your request."

        assistant_message = ConversationMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=rendered_assistant_content,
        )
        db.add(assistant_message)

        content.content = updated_content
        content.updated_at = func.now()

        context.update_key_points(change_summary)
        conversation.context_snapshot = context.to_dict()
        conversation.updated_at = func.now()
        conversation.model = resolved_model

        suggestions = generate_follow_up_suggestions(
            updated_content, change_summary, request.message
        )

        await db.commit()
        # Fetch all messages for response, not just recent ones
        refreshed_messages = await fetch_recent_messages(db, conversation.id, limit=500)

        response = ConversationResponse(
            conversation_id=conversation.id,
            content_id=content.id,
            updated_content=updated_content,
            model_used=resolved_model,
            change_summary=change_summary,
            notes=notes,
            suggestions=suggestions,
            messages=[ConversationMessageOut.model_validate(msg) for msg in refreshed_messages],
            branch_parent_id=conversation.parent_id,
            created_new_conversation=created_new_conversation,
        )
        return response
    except Exception:
        await db.rollback()
        raise


async def delete_conversation(
    db: AsyncSession,
    *,
    conversation_id: str,
    content_id: int,
    user_id: int,
) -> None:
    """Soft-delete a conversation thread if owned by the user.

    Args:
        db: Database session
        conversation_id: ID of the conversation to delete
        content_id: ID of the content the conversation belongs to
        user_id: ID of the user deleting the conversation

    Raises:
        ApplicationException: If conversation not found or user not authorized
    """
    conversation = await get_conversation_for_user(db, conversation_id, user_id, content_id)
    conversation.soft_delete()
    await db.commit()
    logger.info(
        f"Conversation {conversation_id} soft-deleted by user {user_id} for content {content_id}"
    )


async def fetch_conversations_for_content(
    db: AsyncSession, *, content_id: int, user_id: int
) -> List[ConversationSummary]:
    """Fetch all conversations for a piece of content.

    Args:
        db: Database session
        content_id: ID of the content
        user_id: ID of the user

    Returns:
        List of ConversationSummary objects
    """
    content = await get_content_for_user(db, content_id, user_id)
    stmt: Select[tuple[ContentConversation]] = (
        select(ContentConversation)
        .where(
            ContentConversation.content_id == content.id,
            ContentConversation.user_id == user_id,
            ContentConversation.deleted_at.is_(None),
        )
        .options(selectinload(ContentConversation.messages))
        .order_by(ContentConversation.created_at.desc())
    )
    result = await db.execute(stmt)
    conversations = result.scalars().unique().all()

    summaries = []
    for conv in conversations:
        summaries.append(
            ConversationSummary(
                id=conv.id,
                content_id=conv.content_id,
                template_id=conv.template_id,
                template_used=conv.template_used,
                model=conv.model,
                parent_id=conv.parent_id,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=len(conv.messages),
            )
        )
    return summaries


async def fetch_conversation_thread(
    db: AsyncSession,
    *,
    content_id: int,
    user_id: int,
    conversation_id: str,
) -> ConversationThreadOut:
    """Fetch a complete conversation thread with all messages.

    Args:
        db: Database session
        content_id: ID of the content
        user_id: ID of the user
        conversation_id: ID of the conversation

    Returns:
        ConversationThreadOut with full message history
    """
    conversation = await get_conversation_for_user(db, conversation_id, user_id, content_id)

    messages = await fetch_recent_messages(db, conversation.id, limit=500)
    return ConversationThreadOut(
        id=conversation.id,
        content_id=conversation.content_id,
        template_id=conversation.template_id,
        template_used=conversation.template_used,
        model=conversation.model,
        parent_id=conversation.parent_id,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=len(messages),
        messages=[ConversationMessageOut.model_validate(msg) for msg in messages],
    )
