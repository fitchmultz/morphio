"""Utility to create an admin user if one doesn't exist."""

import asyncio
import logging
import os

from sqlalchemy import select

from ..database import AsyncSessionLocal
from ..models.user import User
from ..services.security import get_password_hash
from ..utils.enums import UserRole

logger = logging.getLogger(__name__)


async def ensure_admin_user_exists():
    """
    Check if any admin user exists and create one if not.
    Uses environment variables for admin credentials.
    """
    # Get admin credentials directly from environment variables
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@morphio.io")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    admin_name = os.environ.get("ADMIN_NAME", "Administrator")

    logger.info(f"Checking for admin user with email: {admin_email}")

    if not admin_password:
        logger.warning(
            "ADMIN_PASSWORD environment variable not set. "
            "Cannot create admin user without a password."
        )
        return False

    try:
        async with AsyncSessionLocal() as session:
            # Check if any admin user exists
            admin_exists = await session.scalar(select(User).filter(User.role == UserRole.ADMIN))

            if admin_exists:
                logger.info(f"Admin user already exists with email: {admin_exists.email}")
                return True

            # Check if the specified admin email is already used by a non-admin
            existing_user = await session.scalar(select(User).filter(User.email == admin_email))

            if existing_user:
                logger.info(
                    f"User with email {admin_email} already exists, upgrading to admin role"
                )
                existing_user.role = UserRole.ADMIN
                await session.commit()
                return True

            # Create a new admin user
            logger.info(f"Creating new admin user with email: {admin_email}")
            hashed_password = get_password_hash(admin_password)

            new_admin = User(
                email=admin_email,
                hashed_password=hashed_password,
                display_name=admin_name,
                role=UserRole.ADMIN,
                is_active=True,
            )

            session.add(new_admin)
            await session.commit()
            logger.info(f"Admin user created successfully with email: {admin_email}")
            return True
    except Exception as e:
        logger.error(f"Error creating admin user: {str(e)}", exc_info=True)
        return False


def run_admin_creation():
    """Run the admin creation function."""
    asyncio.run(ensure_admin_user_exists())


if __name__ == "__main__":
    run_admin_creation()
