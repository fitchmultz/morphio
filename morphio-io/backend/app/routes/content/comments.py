"""Comment management routes."""

import logging
from typing import Annotated, List

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...models.content import Content
from ...models.user import User
from ...schemas.comment_schema import CommentCreate, CommentOut, CommentUpdate
from ...schemas.response_schema import ApiResponse
from ...services.comment import (
    create_comment,
    delete_comment,
    get_comments_by_content,
    update_comment,
)
from ...services.security import get_current_user
from ...utils.decorators import require_auth
from ...utils.enums import ResponseStatus
from ...utils.response_utils import create_response
from ...utils.route_helpers import common_responses, handle_route_errors
from .dependencies import get_user_content

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/{content_id}/comments",
    operation_id="create_comment",
    response_model=ApiResponse[CommentOut],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Comment created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Comment created successfully",
                        "data": {
                            "id": 1,
                            "content_id": 1,
                            "user_id": 1,
                            "text": "Great content!",
                            "created_at": "2025-02-19T12:00:00Z",
                            "updated_at": None,
                            "parent_id": None,
                            "author_display_name": "User1",
                        },
                    }
                }
            },
        },
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        404: {"description": "Content not found"},
        **common_responses,
    },
)
@require_auth
@handle_route_errors
async def create_comment_route(
    content_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    comment: CommentCreate = Body(...),
    _content: Content = Depends(get_user_content),
):
    new_comment = await create_comment(db, comment, content_id, int(current_user.id))
    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Comment created successfully",
        data=new_comment.model_dump(),
        status_code=status.HTTP_201_CREATED,
    )


@router.get(
    "/{content_id}/comments",
    operation_id="list_comments",
    response_model=ApiResponse[List[CommentOut]],
    responses={
        200: {
            "description": "Comments retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Comments retrieved successfully",
                        "data": [
                            {
                                "id": 1,
                                "content_id": 1,
                                "user_id": 1,
                                "text": "Great content!",
                                "created_at": "2025-02-19T12:00:00Z",
                                "updated_at": None,
                                "parent_id": None,
                                "author_display_name": "User1",
                            }
                        ],
                    }
                }
            },
        },
        404: {"description": "Content not found"},
        **common_responses,
    },
)
@require_auth
@handle_route_errors
async def get_comments(
    content_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    _content: Content = Depends(get_user_content),
):
    comments = await get_comments_by_content(db, content_id, page, per_page, int(current_user.id))
    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Comments retrieved successfully",
        data=comments,
        status_code=status.HTTP_200_OK,
    )


@router.put(
    "/comments/{comment_id}",
    operation_id="update_comment",
    response_model=ApiResponse[CommentOut],
    responses={
        200: {
            "description": "Comment updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Comment updated successfully",
                        "data": {
                            "id": 1,
                            "content_id": 1,
                            "user_id": 1,
                            "text": "Updated comment!",
                            "created_at": "2025-02-19T12:00:00Z",
                            "updated_at": "2025-02-19T12:01:00Z",
                            "parent_id": None,
                            "author_display_name": "User1",
                        },
                    }
                }
            },
        },
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        404: {"description": "Comment not found or unauthorized"},
        **common_responses,
    },
)
@require_auth
@handle_route_errors
async def update_comment_route(
    comment_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    comment_update: CommentUpdate = Body(...),
):
    updated_comment = await update_comment(db, comment_id, comment_update, int(current_user.id))
    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Comment updated successfully",
        data=updated_comment.model_dump(),
        status_code=status.HTTP_200_OK,
    )


@router.delete(
    "/comments/{comment_id}",
    operation_id="delete_comment",
    response_model=ApiResponse[None],
    responses={
        200: {
            "description": "Comment deleted successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Comment deleted successfully",
                        "data": None,
                    }
                }
            },
        },
        401: {"description": "Unauthorized"},
        404: {"description": "Comment not found or unauthorized"},
        **common_responses,
    },
)
@require_auth
@handle_route_errors
async def delete_comment_route(
    comment_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await delete_comment(db, comment_id, int(current_user.id))
    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Comment deleted successfully",
        data=None,
        status_code=status.HTTP_200_OK,
    )
