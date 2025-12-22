import html
import logging
import re
from typing import Union, overload

from ...schemas.content_schema import ContentCreate, ContentUpdate
from ...utils.error_handlers import ApplicationException

logger = logging.getLogger(__name__)


def validate_content(content: Union[ContentCreate, ContentUpdate]):
    """
    Validate content fields.

    :param content: Content to validate (create or update)
    :raises ApplicationException: If validation fails
    """
    if isinstance(content, ContentCreate) or (
        isinstance(content, ContentUpdate) and content.title is not None
    ):
        title = content.title or ""
        if len(title) > 200:
            raise ApplicationException("Title must be 200 characters or less.")
    if isinstance(content, ContentCreate) or (
        isinstance(content, ContentUpdate) and content.content is not None
    ):
        body = content.content or ""
        if len(body) < 1:
            raise ApplicationException("Content must not be empty.")


@overload
def sanitize_content(content: ContentCreate) -> ContentCreate: ...


@overload
def sanitize_content(content: ContentUpdate) -> ContentUpdate: ...


def sanitize_content(
    content: Union[ContentCreate, ContentUpdate],
) -> Union[ContentCreate, ContentUpdate]:
    """
    Sanitize content fields to prevent XSS attacks while preserving quotation marks.

    :param content: Content to sanitize (create or update)
    :return: Sanitized content (same type as input)
    """
    if isinstance(content, ContentCreate) or (
        isinstance(content, ContentUpdate) and content.title is not None
    ):
        content.title = html.escape(content.title or "", quote=False)
        content.title = re.sub(r"<[^>]*?>", "", content.title)
    if isinstance(content, ContentCreate) or (
        isinstance(content, ContentUpdate) and content.content is not None
    ):
        content.content = html.escape(content.content or "")
    return content
