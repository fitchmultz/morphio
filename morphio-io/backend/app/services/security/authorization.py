import logging
from enum import Enum

from fastapi import status
from sqlalchemy import select

from ...dependencies import CurrentUser, DbSession
from ...models.comment import Comment
from ...models.content import Content
from ...models.template import Template
from ...utils.error_handlers import ApplicationException

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """User permissions enum."""

    ADMIN = "admin"
    USER = "user"


async def check_permission(
    required_permission: Permission,
    user: CurrentUser,
) -> bool:
    """
    Check if the user has the required permission.

    :param required_permission: The required permission
    :param user: The user to check
    :return: True if authorized, raises exception otherwise
    """
    if required_permission == Permission.ADMIN and not user.is_admin:
        raise ApplicationException(
            message="You do not have permission to perform this action",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    return True


async def check_resource_owner(
    resource_id: int,
    resource_type: str,
    user: CurrentUser,
    db: DbSession,
) -> bool:
    """
    Check if the user is the owner of the specified resource.

    :param resource_id: The ID of the resource
    :param resource_type: The type of resource
    :param user: The user to check
    :param db: The database session
    :return: True if authorized, raises exception otherwise
    """
    if user.is_admin:
        return True

    normalized_type = resource_type.lower()
    if normalized_type == "content":
        owner_id = await db.scalar(select(Content.user_id).where(Content.id == resource_id))
    elif normalized_type == "comment":
        owner_id = await db.scalar(select(Comment.user_id).where(Comment.id == resource_id))
    elif normalized_type == "template":
        owner_id = await db.scalar(select(Template.user_id).where(Template.id == resource_id))
        if owner_id is None:
            is_default = await db.scalar(
                select(Template.is_default).where(Template.id == resource_id)
            )
            if is_default:
                return True
    else:
        raise ApplicationException(
            message=f"Unsupported resource type: {resource_type}",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if owner_id != user.id:
        raise ApplicationException(
            message="You do not have permission to access this resource",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    return True


async def get_user_permissions(
    user: CurrentUser,
) -> list[Permission]:
    """
    Get the list of permissions for the user.

    :param user: The user
    :return: List of permissions
    """
    permissions = [Permission.USER]
    if user.is_admin:
        permissions.append(Permission.ADMIN)
    return permissions
