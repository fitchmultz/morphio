"""Conversation service module."""

from .manager import (
    continue_content_conversation,
    delete_conversation,
    fetch_conversation_thread,
    fetch_conversations_for_content,
)
from .repository import (
    HISTORY_LIMIT,
    create_conversation,
    fetch_recent_messages,
    get_content_for_user,
    get_conversation_for_user,
)
from .response_parser import parse_model_response, render_assistant_message, strip_code_fences
from .suggestions import generate_follow_up_suggestions

__all__ = [
    # Manager (orchestration)
    "continue_content_conversation",
    "delete_conversation",
    "fetch_conversation_thread",
    "fetch_conversations_for_content",
    # Repository (CRUD)
    "create_conversation",
    "fetch_recent_messages",
    "get_content_for_user",
    "get_conversation_for_user",
    "HISTORY_LIMIT",
    # Response parsing
    "parse_model_response",
    "render_assistant_message",
    "strip_code_fences",
    # Suggestions
    "generate_follow_up_suggestions",
]
