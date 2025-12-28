import logging
from typing import Annotated, List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.user import User
from ..schemas.response_schema import ApiResponse
from ..schemas.template_schema import TemplateCreate, TemplateOut, TemplateUpdate
from ..services.security import get_current_user
from ..services.template import (
    create_custom_template,
    delete_custom_template,
    get_all_templates,
    get_template_by_id,
    update_custom_template,
    validate_template_content,
)
from ..utils.decorators import cache, rate_limit
from ..utils.response_utils import ResponseStatus, create_response

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/get-templates",
    operation_id="list_templates",
    response_model=ApiResponse[List[TemplateOut]],
    responses={
        200: {
            "description": "Templates retrieved successfully",
        },
    },
)
@rate_limit("100/minute")
@cache(expire=300)
async def get_templates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    templates = await get_all_templates(db, current_user.id)
    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Templates retrieved successfully",
        data=templates,
        status_code=status.HTTP_200_OK,
    )


@router.post(
    "/save-template",
    operation_id="save_template",
    response_model=ApiResponse[TemplateOut],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Template saved successfully",
        },
        400: {
            "description": "Invalid template content",
        },
    },
)
@rate_limit("60/minute")
async def save_template(
    template: TemplateCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    logger.info(f"Attempting to save template for user {current_user.id}")
    await validate_template_content(template.template_content)

    template.user_id = current_user.id
    new_template = await create_custom_template(db, template)
    logger.info(f"Template saved successfully for user {current_user.id}")
    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Template saved successfully",
        data=new_template,
        status_code=status.HTTP_201_CREATED,
    )


@router.get(
    "/get-template/{template_id}",
    operation_id="get_template",
    response_model=ApiResponse[TemplateOut],
    responses={
        200: {
            "description": "Template retrieved successfully",
        },
        404: {"description": "Template not found"},
    },
)
@rate_limit("60/minute")
@cache(expire=300)
async def get_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tmpl = await get_template_by_id(db, template_id, current_user.id)
    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Template retrieved successfully",
        data=tmpl,
        status_code=status.HTTP_200_OK,
    )


@router.put(
    "/update-template/{template_id}",
    operation_id="update_template",
    response_model=ApiResponse[TemplateOut],
    responses={
        200: {
            "description": "Template updated successfully",
        },
        400: {"description": "Invalid template content"},
        404: {"description": "Template not found or unauthorized"},
    },
)
@rate_limit("60/minute")
async def update_template_route(
    template_id: int,
    template_update: TemplateUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    logger.info(f"Updating template {template_id} for user {current_user.id}")

    if template_update.template_content is not None:
        await validate_template_content(template_update.template_content)

    updated_template = await update_custom_template(
        db, template_id, template_update, current_user.id
    )

    logger.info(f"Template {template_id} updated successfully for user {current_user.id}")
    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Template updated successfully",
        data=updated_template,
        status_code=status.HTTP_200_OK,
    )


@router.delete(
    "/delete-template/{template_id}",
    operation_id="delete_template",
    response_model=ApiResponse[None],
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Template deleted successfully",
        },
        404: {"description": "Template not found or unauthorized"},
    },
)
@rate_limit("60/minute")
async def delete_template_route(
    template_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    logger.info(f"Deleting template {template_id} for user {current_user.id}")
    await delete_custom_template(db, template_id, current_user.id)

    logger.info(f"Template {template_id} deleted successfully for user {current_user.id}")
    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Template deleted successfully",
        data=None,
        status_code=status.HTTP_200_OK,
    )
