import logging

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..schemas.content_schema import ContentCreate, ContentUpdate
from ..services.content import sanitize_content, validate_content

logger = logging.getLogger(__name__)


async def validate_and_sanitize_content(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Middleware to validate and sanitize content from request body.

    This middleware extracts content data from the request body,
    validates it for security issues, and then sanitizes it to
    remove potential XSS or other injection vectors.

    Args:
        request: The incoming request that contains content data
        db: Database session for any needed database operations

    Returns:
        AsyncSession: The database session for use in the route handler

    Note:
        The sanitized content is stored in request.state.sanitized_content
        for access by the route handler
    """
    try:
        body = await request.json()
        content = ContentCreate(**body) if request.method == "POST" else ContentUpdate(**body)

        # Validate content for security issues
        validate_content(content)

        # Sanitize to remove XSS and other injection vectors
        sanitized_content = sanitize_content(content)

        # Store the sanitized content in the request state
        request.state.sanitized_content = sanitized_content

        logger.debug(f"Content for {request.url.path} validated and sanitized")
    except Exception as e:
        logger.error(f"Error validating/sanitizing content: {str(e)}", exc_info=True)
        # Allow the exception to propagate to the global exception handler
        raise

    return db
