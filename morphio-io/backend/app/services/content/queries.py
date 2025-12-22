import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.content import Content
from ...models.tag import ContentTag, Tag
from ...schemas.content_schema import ContentOut
from ...schemas.response_schema import PaginatedResponse
from ...schemas.tag_schema import TagOut, TagWithContentCount
from ...utils.response_utils import ResponseStatus, create_response

logger = logging.getLogger(__name__)


async def get_top_content(session: AsyncSession, limit: int = 10):
    """
    Get top content items by view count.

    :param session: The database session
    :param limit: Maximum number of items to return
    :return: Response with paginated top content items
    """
    try:
        result = await session.execute(
            select(Content).order_by(Content.view_count.desc()).limit(limit)
        )
        top_content = result.scalars().all()
        logger.info(f"Retrieved top {limit} content items")
        return create_response(
            status=ResponseStatus.SUCCESS,
            message=f"Retrieved top {limit} content items",
            data=PaginatedResponse(
                items=[ContentOut.model_validate(content) for content in top_content],
                total=len(top_content),
                page=1,
                per_page=limit,
            ).model_dump(),
            status_code=200,
        )
    except Exception as e:
        logger.error(f"Error retrieving top content: {str(e)}", exc_info=True)
        return create_response(
            status=ResponseStatus.ERROR,
            message="Failed to retrieve top content",
            data={"error": str(e)},
            status_code=500,
        )


async def get_trending_tags(session: AsyncSession, limit: int = 5):
    """
    Get trending tags by content count.

    :param session: The database session
    :param limit: Maximum number of tags to return
    :return: Response with trending tags
    """
    try:
        result = await session.execute(
            select(Tag, func.count(ContentTag.content_id).label("content_count"))
            .join(ContentTag)
            .group_by(Tag)
            .order_by(func.count(ContentTag.content_id).desc())
            .limit(limit)
        )
        trending_tags = result.all()
        logger.info(f"Retrieved top {limit} trending tags")
        return create_response(
            status=ResponseStatus.SUCCESS,
            message=f"Retrieved top {limit} trending tags",
            data={
                "trending_tags": [
                    TagWithContentCount(
                        **TagOut.model_validate(tag).model_dump(), content_count=count
                    )
                    for tag, count in trending_tags
                ]
            },
            status_code=200,
        )
    except Exception as e:
        logger.error(f"Error retrieving trending tags: {str(e)}", exc_info=True)
        return create_response(
            status=ResponseStatus.ERROR,
            message="Failed to retrieve trending tags",
            data={"error": str(e)},
            status_code=500,
        )
