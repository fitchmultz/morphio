"""Content CRUD operations."""

import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, Body, Depends, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...database import get_db
from ...models.content import Content
from ...models.user import User
from ...schemas.content_schema import (
    ContentCreate,
    ContentOut,
    ContentTitleUpdate,
    ContentUpdate,
)
from ...schemas.response_schema import ApiResponse, PaginatedResponse
from ...services.content import resolve_content_tags, sanitize_content, validate_content
from ...services.generation import update_content_title
from ...services.security import get_current_user
from ...utils.decorators import cache, rate_limit, require_auth
from ...utils.database_utils import PaginatedQuery
from ...utils.enums import ResponseStatus
from ...utils.error_handlers import ApplicationException
from ...utils.response_utils import create_response
from ...utils.route_helpers import common_responses, handle_route_errors
from .dependencies import get_user_content

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/save-content",
    operation_id="save_content",
    response_model=ApiResponse[ContentOut],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Content saved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Content saved successfully",
                        "data": {
                            "id": 1,
                            "title": "My Awesome Content",
                            "content": "This is some great content!",
                            "created_at": "2023-04-01T12:00:00Z",
                            "updated_at": "2023-04-01T12:00:00Z",
                        },
                    }
                }
            },
        },
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        **common_responses,
    },
)
@require_auth
@handle_route_errors
async def save_content(
    content: ContentCreate = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    validate_content(content)
    sanitized_content = sanitize_content(content)
    sanitized_content.user_id = current_user.id
    payload = sanitized_content.model_dump(exclude={"tags"})
    db_content = Content(**payload)
    db_content.tags = await resolve_content_tags(db, sanitized_content.tags)
    db.add(db_content)
    await db.commit()
    await db.refresh(db_content)

    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Content saved successfully",
        data=ContentOut.model_validate(db_content).model_dump(),
        status_code=status.HTTP_201_CREATED,
    )


@router.get(
    "/get-contents",
    operation_id="list_contents",
    response_model=ApiResponse[PaginatedResponse[ContentOut]],
    responses={
        200: {
            "description": "Contents retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Contents retrieved successfully",
                        "data": {
                            "items": [
                                {
                                    "id": 1,
                                    "title": "Content 1",
                                    "content": "Body of content 1",
                                    "created_at": "2023-04-01T12:00:00Z",
                                    "updated_at": "2023-04-01T12:00:00Z",
                                },
                            ],
                            "total": 10,
                            "page": 1,
                            "per_page": 2,
                        },
                    }
                }
            },
        },
        401: {"description": "Unauthorized"},
        **common_responses,
    },
)
@handle_route_errors
async def get_contents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(5, ge=1, le=100),
    template_id: Optional[int] = Query(None, description="Filter by template ID"),
):
    filters = [Content.user_id == current_user.id, Content.deleted_at.is_(None)]
    if template_id:
        filters.append(Content.template_id == template_id)

    query = PaginatedQuery(
        model=Content,
        filters=filters,
        order_by=Content.created_at.desc(),
        options=[selectinload(Content.user), selectinload(Content.tags)],
    )
    result = await query.execute(db, page, per_page)

    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Contents retrieved successfully",
        data=PaginatedResponse(
            items=[ContentOut.model_validate(content) for content in result.items],
            total=result.total,
            page=page,
            per_page=per_page,
        ).model_dump(),
        status_code=status.HTTP_200_OK,
    )


@router.get(
    "/get-content/{content_id}",
    operation_id="get_content",
    response_model=ApiResponse[ContentOut],
    responses={
        200: {
            "description": "Content retrieved successfully",
        },
        401: {"description": "Unauthorized"},
        404: {
            "description": "Not Found",
        },
        **common_responses,
    },
)
@rate_limit("100/minute")
@cache(expire=300)
@handle_route_errors
async def get_content(
    content_id: int,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    content: Content = Depends(get_user_content),
):
    logger.info(f"Content retrieved: {content_id} by user {current_user.id}")
    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Content retrieved successfully",
        data=ContentOut.model_validate(content).model_dump(),
        status_code=status.HTTP_200_OK,
    )


@router.put(
    "/update-content/{content_id}",
    operation_id="update_content",
    response_model=ApiResponse[ContentOut],
    responses={
        200: {
            "description": "Content updated successfully",
        },
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        404: {"description": "Not Found"},
        **common_responses,
    },
)
@rate_limit("100/minute")
@handle_route_errors
async def update_content(
    content_id: int,
    request: Request,
    content_update: ContentUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    validate_content(content_update)
    sanitized_content = sanitize_content(content_update)

    query = select(Content).where(
        Content.id == content_id,
        Content.user_id == current_user.id,
        Content.deleted_at.is_(None),
    )
    result = await db.execute(query)
    content = result.unique().scalar_one_or_none()

    if not content:
        raise ApplicationException(
            message="Content not found or unauthorized",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    update_payload = sanitized_content.model_dump(exclude_unset=True, exclude={"tags"})
    for field, value in update_payload.items():
        setattr(content, field, value)
    if sanitized_content.tags is not None:
        content.tags = await resolve_content_tags(db, sanitized_content.tags)

    await db.commit()
    await db.refresh(content)

    logger.info(f"Content updated: {content_id} by user {current_user.id}")
    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Content updated successfully",
        data=ContentOut.model_validate(content).model_dump(),
        status_code=status.HTTP_200_OK,
    )


@router.put(
    "/update-multiple-contents",
    operation_id="update_multiple_contents",
    response_model=ApiResponse[List[ContentOut]],
    responses={
        200: {
            "description": "Contents updated successfully",
        },
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        **common_responses,
    },
)
@rate_limit("100/minute")
@handle_route_errors
async def update_multiple_contents(
    request: Request,
    contents: List[ContentUpdate],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Filter out updates without an id
    content_ids = [cid for cid in (c.id for c in contents) if cid is not None]
    query = select(Content).where(
        Content.id.in_(content_ids),
        Content.user_id == current_user.id,
        Content.deleted_at.is_(None),
    )
    result = await db.execute(query)
    existing_contents: dict[int, Content] = {int(c.id): c for c in result.unique().scalars().all()}

    updated_contents = []
    for content_update in contents:
        validate_content(content_update)
        sanitized_content = sanitize_content(content_update)
        cid = content_update.id
        if cid is not None and cid in existing_contents:
            content_obj = existing_contents[cid]
            update_payload = sanitized_content.model_dump(exclude_unset=True, exclude={"tags"})
            for field, value in update_payload.items():
                setattr(content_obj, field, value)
            if sanitized_content.tags is not None:
                content_obj.tags = await resolve_content_tags(db, sanitized_content.tags)
            updated_contents.append(content_obj)

    await db.commit()
    for content_obj in updated_contents:
        await db.refresh(content_obj)

    logger.info(f"Updated {len(updated_contents)} contents for user {current_user.id}")
    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Contents updated successfully",
        data=[ContentOut.model_validate(c).model_dump() for c in updated_contents],
        status_code=status.HTTP_200_OK,
    )


@router.put(
    "/update-title/{content_id}",
    operation_id="update_content_title",
    response_model=ApiResponse[ContentOut],
    responses={
        200: {
            "description": "Content title updated successfully",
        },
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        404: {"description": "Not Found"},
        **common_responses,
    },
)
@rate_limit("100/minute")
@handle_route_errors
async def update_content_title_route(
    content_id: int,
    request: Request,
    title_update: ContentTitleUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
):
    validate_content(ContentUpdate(title=title_update.title, content=None))
    sanitized_title = sanitize_content(ContentUpdate(title=title_update.title, content=None)).title
    assert sanitized_title is not None
    updated_content = await update_content_title(content_id, sanitized_title, int(current_user.id))
    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Content title updated successfully",
        data=ContentOut.model_validate(updated_content).model_dump()
        if not isinstance(updated_content, dict)
        else updated_content,
        status_code=status.HTTP_200_OK,
    )


@router.delete(
    "/delete-content/{content_id}",
    operation_id="delete_content",
    status_code=status.HTTP_200_OK,
    response_model=ApiResponse[None],
    responses={
        200: {
            "description": "Content deleted successfully",
        },
        401: {"description": "Unauthorized"},
        404: {
            "description": "Not Found",
            "content": {
                "application/json": {"example": {"detail": "Content not found or unauthorized"}}
            },
        },
        **common_responses,
    },
)
@rate_limit("30/minute")
@handle_route_errors
async def delete_content(
    content_id: int,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    content: Content = Depends(get_user_content),
):
    content.soft_delete()
    await db.commit()

    logger.info(f"Content soft-deleted: {content_id} by user {current_user.id}")
    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Content deleted successfully",
        status_code=status.HTTP_200_OK,
    )
