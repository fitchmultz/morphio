import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ...database import engine
from ...models.content import Content
from ...schemas.content_schema import ContentCreate, ContentOut
from ...utils.error_handlers import ApplicationException
from .core import generate_content_title

logger = logging.getLogger(__name__)


async def save_generated_content(
    content: str, user_id: int, template_id: int | None = None
) -> ContentOut:
    """Generate a title and save content to the database."""
    try:
        title = await generate_content_title(content)
        new_content = ContentCreate(
            title=title, content=content, user_id=user_id, template_id=template_id
        )
        async with AsyncSession(engine) as session:
            db_content = Content(**new_content.model_dump())
            session.add(db_content)
            await session.commit()
            await session.refresh(db_content, attribute_names=["user", "template"])

        logger.info(
            f"Automatically saved content '{title}' for user {user_id} with template {template_id}"
        )
        return ContentOut.model_validate(db_content)
    except Exception as e:
        logger.error(f"Error auto-saving content for user {user_id}: {str(e)}", exc_info=True)
        raise ApplicationException("Failed to save content.", status_code=500)


async def update_content_title(content_id: int, new_title: str, user_id: int) -> ContentOut:
    """Update the title of an existing content item."""
    async with AsyncSession(engine) as session:
        query = (
            select(Content)
            .options(joinedload(Content.user), joinedload(Content.tags))
            .where(Content.id == content_id, Content.user_id == user_id)
        )
        result = await session.execute(query)
        content = result.unique().scalar_one_or_none()

        if not content:
            raise ApplicationException("Content not found or unauthorized", status_code=404)

        setattr(content, "title", new_title)
        setattr(content, "updated_at", func.now())
        await session.commit()
        await session.refresh(content, attribute_names=["user", "tags"])

    logger.info(f"Updated title for content {content_id} by user {user_id}")
    return ContentOut.model_validate(content)
