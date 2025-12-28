"""Conversation handling routes."""

import logging
from typing import Annotated, List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...models.user import User
from ...schemas.conversation_schema import (
    ConversationRequest,
    ConversationResponse,
    ConversationSummary,
    ConversationThreadOut,
)
from ...schemas.response_schema import ApiResponse
from ...services.conversation import (
    continue_content_conversation,
    delete_conversation,
    fetch_conversation_thread,
    fetch_conversations_for_content,
)
from ...services.security import get_current_user
from ...utils.decorators import rate_limit, require_auth
from ...utils.enums import ResponseStatus
from ...utils.response_utils import create_response
from ...utils.route_helpers import common_responses, handle_route_errors

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/{content_id}/conversations",
    operation_id="list_content_conversations",
    response_model=ApiResponse[List[ConversationSummary]],
    responses={
        200: {"description": "Conversations retrieved successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Content not found"},
        **common_responses,
    },
)
@require_auth
@handle_route_errors
async def list_content_conversations(
    content_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    conversations = await fetch_conversations_for_content(
        db, content_id=content_id, user_id=current_user.id
    )
    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Conversations retrieved successfully",
        data=[summary.model_dump() for summary in conversations],
        status_code=status.HTTP_200_OK,
    )


@router.get(
    "/{content_id}/conversations/{conversation_id}",
    operation_id="get_conversation_thread",
    response_model=ApiResponse[ConversationThreadOut],
    responses={
        200: {"description": "Conversation retrieved successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Conversation not found"},
        **common_responses,
    },
)
@require_auth
@handle_route_errors
async def get_conversation_thread(
    content_id: int,
    conversation_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    thread = await fetch_conversation_thread(
        db,
        content_id=content_id,
        user_id=current_user.id,
        conversation_id=conversation_id,
    )
    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Conversation retrieved successfully",
        data=thread.model_dump(),
        status_code=status.HTTP_200_OK,
    )


@router.delete(
    "/{content_id}/conversations/{conversation_id}",
    operation_id="delete_conversation",
    response_model=ApiResponse[None],
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Conversation deleted successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Conversation deleted successfully",
                        "data": None,
                    }
                }
            },
        },
        401: {"description": "Unauthorized"},
        404: {"description": "Conversation not found or unauthorized"},
        **common_responses,
    },
)
@require_auth
@rate_limit("30/minute")
@handle_route_errors
async def delete_conversation_route(
    content_id: int,
    conversation_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await delete_conversation(
        db,
        conversation_id=conversation_id,
        content_id=content_id,
        user_id=current_user.id,
    )
    logger.info(
        f"Conversation {conversation_id} deleted by user {current_user.id} for content {content_id}"
    )
    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Conversation deleted successfully",
        data=None,
        status_code=status.HTTP_200_OK,
    )


@router.post(
    "/{content_id}/conversation",
    operation_id="continue_conversation",
    response_model=ApiResponse[ConversationResponse],
    responses={
        200: {"description": "Conversation updated successfully"},
        400: {"description": "Bad request"},
        401: {"description": "Unauthorized"},
        404: {"description": "Content or conversation not found"},
        **common_responses,
    },
)
@require_auth
@handle_route_errors
async def continue_content_conversation_route(
    content_id: int,
    payload: ConversationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await continue_content_conversation(
        db,
        content_id=content_id,
        user_id=current_user.id,
        request=payload,
    )
    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Conversation updated successfully",
        data=result.model_dump(),
        status_code=status.HTTP_200_OK,
    )
