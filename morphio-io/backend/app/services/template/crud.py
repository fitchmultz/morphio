"""Template CRUD operations for managing templates in the database."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

# Third-party imports
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# Application imports
from ...models.template import Template as TemplateModel
from ...schemas.template_schema import TemplateCreate, TemplateUpdate

# Local imports
from .exceptions import (
    DefaultTemplateEditException,
    DuplicateTemplateNameException,
    TemplateNotFoundException,
    TemplateNotOwnedException,
)

logger = logging.getLogger(__name__)


async def get_all_templates(db: AsyncSession, user_id: int) -> List[Dict[str, Any]]:
    """
    Get all templates visible to a user (user-owned + default templates)

    Args:
        db: Database session
        user_id: The user ID

    Returns:
        List[Dict[str, Any]]: List of template dictionaries
    """
    stmt = select(TemplateModel).where(
        or_(TemplateModel.user_id == user_id, TemplateModel.is_default.is_(True))
    )
    result = await db.execute(stmt)
    templates = result.scalars().all()

    # Special case for transcript-only template (id 0)
    templates_list = [
        {
            "id": 0,
            "name": "Transcript Only",
            "is_default": True,
            "user_id": None,
            "template_content": "",  # Add empty template content
            "created_at": datetime.now(),  # Add current time as placeholder
        }
    ]

    # Add all regular templates
    for template in templates:
        templates_list.append(
            {
                "id": template.id,
                "name": template.name,
                "is_default": template.is_default,
                "user_id": template.user_id,
                "template_content": template.template_content,  # Include template content
                "created_at": template.created_at,  # Include creation timestamp
            }
        )

    return templates_list


async def get_template_by_id(db: AsyncSession, template_id: int, user_id: int) -> Dict[str, Any]:
    """
    Get a template by ID

    Args:
        db: Database session
        template_id: The template ID
        user_id: The user ID

    Returns:
        Dict[str, Any]: Template data

    Raises:
        TemplateNotFoundException: If template not found
    """
    # Special case for transcript-only template (id 0)
    if template_id == 0:
        return {
            "id": 0,
            "name": "Transcript Only",
            "template_content": "",
            "is_default": True,
            "user_id": None,
            "created_at": datetime.now(),  # Add created_at field
        }

    stmt = select(TemplateModel).where(TemplateModel.id == template_id)
    result = await db.execute(stmt)
    template = result.scalars().first()

    if not template:
        raise TemplateNotFoundException(f"Template with ID {template_id} not found")

    # Check if user has access to the template
    if not template.is_default and template.user_id != user_id:
        raise TemplateNotOwnedException(
            f"Template with ID {template_id} is not owned by user {user_id}"
        )

    return {
        "id": template.id,
        "name": template.name,
        "template_content": template.template_content,
        "is_default": template.is_default,
        "user_id": template.user_id,
        "created_at": template.created_at,  # Add created_at field
    }


async def create_custom_template(db: AsyncSession, template_data: TemplateCreate) -> Dict[str, Any]:
    """
    Create a new custom template

    Args:
        db: Database session
        template_data: Template creation data

    Returns:
        Dict[str, Any]: Created template data

    Raises:
        DuplicateTemplateNameException: If template name already exists for user
    """
    # Check if template name already exists for this user
    stmt = select(TemplateModel).where(
        TemplateModel.name == template_data.name,
        TemplateModel.user_id == template_data.user_id,
    )
    result = await db.execute(stmt)
    if result.scalars().first():
        error_msg = (
            f"Template with name '{template_data.name}' already exists "
            f"for user {template_data.user_id}"
        )
        raise DuplicateTemplateNameException(error_msg)

    # Create new template
    template = TemplateModel(
        name=template_data.name,
        template_content=template_data.template_content,
        is_default=False,
        user_id=template_data.user_id,
    )

    db.add(template)
    await db.commit()
    await db.refresh(template)

    return {
        "id": template.id,
        "name": template.name,
        "template_content": template.template_content,
        "is_default": template.is_default,
        "user_id": template.user_id,
        "created_at": template.created_at,  # Add created_at field
    }


async def update_custom_template(
    db: AsyncSession, template_id: int, template_update: TemplateUpdate, user_id: int
) -> Dict[str, Any]:
    """
    Update a custom template

    Args:
        db: Database session
        template_id: The template ID to update
        template_update: Template update data
        user_id: The user ID

    Returns:
        Dict[str, Any]: Updated template data

    Raises:
        TemplateNotFoundException: If template not found
        TemplateNotOwnedException: If template not owned by user
        DefaultTemplateEditException: If trying to edit a default template
        DuplicateTemplateNameException: If new name already exists for user
    """
    # Get the template
    stmt = select(TemplateModel).where(TemplateModel.id == template_id)
    result = await db.execute(stmt)
    template = result.scalars().first()

    if not template:
        raise TemplateNotFoundException(f"Template with ID {template_id} not found")

    # Check if template is a default template
    if template.is_default:
        raise DefaultTemplateEditException(f"Cannot update default template with ID {template_id}")

    # Check if template is owned by the user
    if template.user_id != user_id:
        raise TemplateNotOwnedException(
            f"Template with ID {template_id} is not owned by user {user_id}"
        )

    # If name is being updated, check for duplicates
    if template_update.name and template_update.name != template.name:
        stmt = select(TemplateModel).where(
            TemplateModel.name == template_update.name, TemplateModel.user_id == user_id
        )
        result = await db.execute(stmt)
        if result.scalars().first():
            raise DuplicateTemplateNameException(
                f"Template with name '{template_update.name}' already exists for user {user_id}"
            )
        template.name = template_update.name

    # Update content if provided
    if template_update.template_content:
        template.template_content = template_update.template_content

    await db.commit()
    await db.refresh(template)

    return {
        "id": template.id,
        "name": template.name,
        "template_content": template.template_content,
        "is_default": template.is_default,
        "user_id": template.user_id,
        "created_at": template.created_at,  # Add created_at field
    }


async def delete_custom_template(
    db: AsyncSession, template_id: int, user_id: int
) -> Dict[str, str]:
    """
    Delete a custom template

    Args:
        db: Database session
        template_id: The template ID to delete
        user_id: The user ID

    Returns:
        Dict[str, str]: Success message

    Raises:
        TemplateNotFoundException: If template not found
        TemplateNotOwnedException: If template not owned by user
        DefaultTemplateEditException: If trying to delete a default template
    """
    # Cannot delete the transcript-only pseudo-template
    if template_id == 0:
        raise DefaultTemplateEditException("Cannot delete the Transcript-Only template")

    # Get the template
    stmt = select(TemplateModel).where(TemplateModel.id == template_id)
    result = await db.execute(stmt)
    template = result.scalars().first()

    if not template:
        raise TemplateNotFoundException(f"Template with ID {template_id} not found")

    # Check if template is a default template
    if template.is_default:
        raise DefaultTemplateEditException(f"Cannot delete default template with ID {template_id}")

    # Check if template is owned by the user
    if template.user_id != user_id:
        raise TemplateNotOwnedException(
            f"Template with ID {template_id} is not owned by user {user_id}"
        )

    await db.delete(template)
    await db.commit()

    return {"message": f"Template with ID {template_id} deleted successfully"}


async def get_template_by_name(db: AsyncSession, template_name: str) -> Optional[int]:
    """
    Get template ID by name

    Args:
        db: Database session
        template_name: The template name

    Returns:
        Optional[int]: Template ID if found, None otherwise

    Raises:
        TemplateNotFoundException: If template not found
    """
    # Special case for transcript-only template
    if template_name == "0":
        return 0

    stmt = select(TemplateModel.id).where(TemplateModel.name == template_name)
    result = await db.execute(stmt)
    template_id = result.scalar_one_or_none()

    if not template_id:
        raise TemplateNotFoundException(f"Template with name '{template_name}' not found")

    return template_id
