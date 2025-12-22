import logging
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...models.comment import Comment
from ...schemas.comment_schema import CommentCreate, CommentOut, CommentUpdate
from ...utils.error_handlers import ApplicationException
from ...utils.response_utils import utc_now

logger = logging.getLogger(__name__)


async def create_comment(
    db: AsyncSession, comment: CommentCreate, content_id: int, user_id: int
) -> CommentOut:
    """
    Create a new comment associated with content and user.

    :param db: Database session
    :param comment: Comment data to create
    :param content_id: ID of the content being commented on
    :param user_id: ID of the user creating the comment
    :return: Created comment data
    """
    db_comment = Comment(
        content_id=content_id,
        user_id=user_id,
        text=comment.text,
        parent_id=comment.parent_id,
        created_at=utc_now(),
    )
    db.add(db_comment)
    await db.commit()
    await db.refresh(db_comment, ["author", "content"])
    logger.info(f"Comment created: {db_comment.id} for content {content_id}")
    return CommentOut.model_validate(db_comment)


from typing import Optional


async def get_comments_by_content(
    db: AsyncSession, content_id: int, page: int, per_page: int, user_id: Optional[int] = None
) -> List[CommentOut]:
    """
    Retrieve paginated comments for a given content ID, optionally filtered by user.

    :param db: Database session
    :param content_id: ID of the content to get comments for
    :param page: Page number (1-indexed)
    :param per_page: Number of comments per page
    :param user_id: Optional user ID to filter comments by user
    :return: List of comments
    """
    query = (
        select(Comment)
        .where(Comment.content_id == content_id, Comment.deleted_at.is_(None))
        .options(selectinload(Comment.author), selectinload(Comment.replies))
        .order_by(Comment.created_at.desc())
    )
    if user_id:
        query = query.where(Comment.user_id == user_id)

    offset = (page - 1) * per_page
    result = await db.execute(query.offset(offset).limit(per_page))
    comments = result.scalars().all()
    return [CommentOut.model_validate(comment) for comment in comments]


async def update_comment(
    db: AsyncSession, comment_id: int, comment_update: CommentUpdate, user_id: int
) -> CommentOut:
    """
    Update an existing comment if owned by the user.

    :param db: Database session
    :param comment_id: ID of the comment to update
    :param comment_update: Updated comment data
    :param user_id: ID of the user updating the comment
    :return: Updated comment data
    :raises ApplicationException: If comment not found or user not authorized
    """
    query = select(Comment).where(
        Comment.id == comment_id,
        Comment.user_id == user_id,
        Comment.deleted_at.is_(None),
    )
    result = await db.execute(query)
    comment = result.scalar_one_or_none()
    if not comment:
        raise ApplicationException(
            message="Comment not found or unauthorized",
            status_code=404,
        )

    comment.text = comment_update.text
    comment.updated_at = utc_now()
    await db.commit()
    await db.refresh(comment, ["author"])
    logger.info(f"Comment updated: {comment_id}")
    return CommentOut.model_validate(comment)


async def delete_comment(db: AsyncSession, comment_id: int, user_id: int) -> None:
    """
    Soft-delete a comment if owned by the user.

    :param db: Database session
    :param comment_id: ID of the comment to delete
    :param user_id: ID of the user deleting the comment
    :raises ApplicationException: If comment not found or user not authorized
    """
    query = select(Comment).where(
        Comment.id == comment_id,
        Comment.user_id == user_id,
        Comment.deleted_at.is_(None),
    )
    result = await db.execute(query)
    comment = result.scalar_one_or_none()
    if not comment:
        raise ApplicationException(
            message="Comment not found or unauthorized",
            status_code=404,
        )

    comment.soft_delete()
    await db.commit()
    logger.info(f"Comment soft-deleted: {comment_id}")
