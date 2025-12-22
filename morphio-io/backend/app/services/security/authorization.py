import logging
from enum import Enum
from typing import List

from fastapi import Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...models.user import User
from ...utils.error_handlers import ApplicationException
from .authentication import get_current_user

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """User permissions enum."""

    ADMIN = "admin"
    USER = "user"
    # Add more permissions as needed


async def check_permission(
    required_permission: Permission,
    user: User = Depends(get_current_user),
) -> bool:
    """
    Check if the user has the required permission.

    :param required_permission: The required permission
    :param user: The user to check
    :return: True if authorized, raises exception otherwise
    """
    # This is a placeholder implementation - customize based on your permission model
    if required_permission == Permission.ADMIN and not user.is_admin:
        raise ApplicationException(
            message="You do not have permission to perform this action",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    return True


async def check_resource_owner(
    resource_id: int,
    resource_type: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> bool:
    """
    Check if the user is the owner of the specified resource.

    :param resource_id: The ID of the resource
    :param resource_type: The type of resource
    :param user: The user to check
    :param db: The database session
    :return: True if authorized, raises exception otherwise
    """
    # This is a placeholder implementation - customize based on your data model
    # Example:
    # if resource_type == "content":
    #     resource = await db.scalar(
    #         select(Content).where(Content.id == resource_id)
    #     )
    #     if not resource or resource.user_id != user.id:
    #         raise ApplicationException(
    #             message="You do not have permission to access this resource",
    #             status_code=status.HTTP_403_FORBIDDEN,
    #         )

    # For now, just return True as a placeholder
    return True


async def get_user_permissions(
    user: User = Depends(get_current_user),
) -> List[Permission]:
    """
    Get the list of permissions for the user.

    :param user: The user
    :return: List of permissions
    """
    # This is a placeholder implementation - customize based on your permission model
    permissions = [Permission.USER]
    if user.is_admin:
        permissions.append(Permission.ADMIN)
    return permissions
