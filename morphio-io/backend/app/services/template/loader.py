"""Template loading and validation functionality."""

import json
import logging
import os
from typing import Union

# Third-party imports
import aiofiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# Application imports
from ...config import settings
from ...models.template import Template as TemplateModel

# Local imports
from .exceptions import TemplateNotFoundException

logger = logging.getLogger(__name__)


async def validate_template_content(template_content: str) -> bool:
    """
    Validates that a template includes the {transcript} placeholder

    Args:
        template_content: The template content to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if "{transcript}" not in template_content:
        return False
    return True


async def template_exists(template_identifier: Union[int, str], db: AsyncSession) -> bool:
    """
    Check if a template exists

    Args:
        template_identifier: A template ID (int) or name (str)
        db: Database session

    Returns:
        bool: True if template exists
    """
    if isinstance(template_identifier, int):
        return await _custom_template_exists(template_identifier, db)
    else:
        return await _default_template_exists(template_identifier)


async def load_template(template_identifier: Union[int, str], db: AsyncSession) -> str:
    """
    Load a template by its identifier

    Args:
        template_identifier: A template ID (int) or name (str)
        db: Database session

    Returns:
        str: The template content

    Raises:
        TemplateNotFoundException: If the template is not found
    """
    # Template ID 0 is a special case for "no template" (just transcript)
    if template_identifier == 0 or template_identifier == "0":
        return ""

    if isinstance(template_identifier, int):
        return await _load_custom_template_by_id(template_identifier, db)
    else:
        return await _load_default_template_by_name(template_identifier)


async def _load_custom_template_by_id(template_id: int, db: AsyncSession) -> str:
    """
    Load a custom template by ID from the database

    Args:
        template_id: The template ID
        db: Database session

    Returns:
        str: The template content

    Raises:
        TemplateNotFoundException: If the template is not found
    """
    stmt = select(TemplateModel).where(TemplateModel.id == template_id)
    result = await db.execute(stmt)
    template = result.scalars().first()

    if not template:
        raise TemplateNotFoundException(f"Custom template with ID {template_id} not found")

    return template.template_content


async def _load_default_template_by_name(template_name: str) -> str:
    """
    Load a default template by name from the templates directory

    Args:
        template_name: The template name

    Returns:
        str: The template content

    Raises:
        FileNotFoundError: If the template file is not found
    """
    # First try direct filename match
    template_file = os.path.join(settings.TEMPLATE_DIR, f"{template_name}.json")

    if not os.path.exists(template_file):
        # If not found, try to find by template "name" property in JSON files
        found = False
        templates_dir = settings.TEMPLATE_DIR

        for filename in os.listdir(templates_dir):
            if filename.endswith(".json"):
                try:
                    file_path = os.path.join(templates_dir, filename)
                    async with aiofiles.open(file_path, mode="r") as f:
                        content = await f.read()
                        template_data = json.loads(content)
                        if template_data.get("name") == template_name:
                            template_file = file_path
                            found = True
                            break
                except (json.JSONDecodeError, IOError) as e:
                    # Skip files with errors
                    logger.debug(f"Error reading template {filename}: {e}")
                    continue

        if not found:
            raise TemplateNotFoundException(f"Default template '{template_name}' not found")

    try:
        async with aiofiles.open(template_file, mode="r") as f:
            content = await f.read()
            template_data = json.loads(content)
            return template_data.get("template_content", "")
    except FileNotFoundError:
        raise TemplateNotFoundException(f"Default template '{template_name}' not found")


async def _custom_template_exists(template_id: int, db: AsyncSession) -> bool:
    """
    Check if a custom template exists in the database

    Args:
        template_id: The template ID
        db: Database session

    Returns:
        bool: True if template exists
    """
    stmt = select(TemplateModel).where(TemplateModel.id == template_id)
    result = await db.execute(stmt)
    return result.scalars().first() is not None


async def _default_template_exists(template_name: str) -> bool:
    """
    Check if a default template exists in the file system

    Args:
        template_name: The template name

    Returns:
        bool: True if template exists
    """
    # First check by filename
    template_file = os.path.join(settings.TEMPLATE_DIR, f"{template_name}.json")

    if os.path.exists(template_file):
        return True

    # If not found by filename, check by template name property in JSON
    templates_dir = settings.TEMPLATE_DIR

    for filename in os.listdir(templates_dir):
        if filename.endswith(".json"):
            try:
                file_path = os.path.join(templates_dir, filename)
                async with aiofiles.open(file_path, mode="r") as f:
                    content = await f.read()
                    template_data = json.loads(content)
                    if template_data.get("name") == template_name:
                        return True
            except (json.JSONDecodeError, IOError) as e:
                # Skip files with errors
                logger.debug(f"Error reading template {filename}: {e}")
                continue

    return False


async def insert_default_templates(db: AsyncSession) -> dict:
    """
    Insert or synchronize default templates from templates directory into the database

    Args:
        db: Database session

    Returns:
        dict: Results of the operation with inserted, updated, and removed counts
    """
    template_files = []
    templates_dir = settings.TEMPLATE_DIR

    # Create templates directory if it doesn't exist
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
        logger.info(f"Created templates directory: {templates_dir}")
        return {"inserted": 0, "updated": 0, "removed": 0}

    # Get all template files
    for filename in os.listdir(templates_dir):
        if filename.endswith(".json"):
            template_files.append(os.path.join(templates_dir, filename))

    # Get existing default templates from database
    stmt = select(TemplateModel).where(TemplateModel.is_default.is_(True))
    result = await db.execute(stmt)
    existing_templates = {t.name: t for t in result.scalars().all()}

    # Track statistics
    stats = {"inserted": 0, "updated": 0, "removed": 0}
    processed_names = set()

    # Process each template file
    for template_file in template_files:
        try:
            async with aiofiles.open(template_file, mode="r") as f:
                content = await f.read()
                template_data = json.loads(content)

                # Use the filename as a fallback if "name" is not in the JSON
                filename_base = os.path.splitext(os.path.basename(template_file))[0]
                template_name = template_data.get("name", filename_base)
                processed_names.add(template_name)

                # Check if template already exists
                if template_name in existing_templates:
                    existing_template = existing_templates[template_name]
                    # Update if content has changed
                    template_content = template_data.get("template_content", "")
                    if existing_template.template_content != template_content:
                        existing_template.template_content = template_content
                        stats["updated"] += 1
                else:
                    # Create new template
                    new_template = TemplateModel(
                        name=template_name,
                        template_content=template_data.get("template_content", ""),
                        is_default=True,
                        user_id=None,
                    )
                    db.add(new_template)
                    stats["inserted"] += 1

        except Exception as e:
            logger.error(f"Error processing template file {template_file}: {e}")

    # Remove templates that no longer exist in the file system
    for name, template in existing_templates.items():
        if name not in processed_names:
            await db.delete(template)
            stats["removed"] += 1

    await db.commit()

    if stats["inserted"] == 0 and stats["updated"] == 0 and stats["removed"] == 0:
        logger.info("All templates are up-to-date. No changes needed.")
    else:
        logger.info(
            f"Templates synchronized: "
            f"{stats['inserted']} inserted, "
            f"{stats['updated']} updated, "
            f"{stats['removed']} removed"
        )
    return stats
