#!/usr/bin/env python3
"""
Standalone script to create an admin user in the database.
Run this script directly to create an admin user manually.

Example usage:
    python -m scripts.create_admin --email=admin@morphio.io --password=StrongPassword123 --name="Admin User"
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import the app modules
sys.path.append(str(Path(__file__).parent.parent))

from app.config import settings
from app.utils.create_admin import ensure_admin_user_exists

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def create_admin_user(email: str, password: str, name: str) -> bool:
    """Create an admin user with the given credentials."""
    # Access settings directly
    settings.ADMIN_EMAIL = email
    settings.ADMIN_PASSWORD = password
    settings.ADMIN_NAME = name

    # For backward compatibility, also set environment variables
    os.environ["ADMIN_EMAIL"] = email
    os.environ["ADMIN_PASSWORD"] = password
    os.environ["ADMIN_NAME"] = name

    logger.info(f"Creating admin user '{name}' with email: {email}")
    success = await ensure_admin_user_exists()
    return success


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Create an admin user in the database.")
    parser.add_argument(
        "--email", type=str, default="admin@morphio.io", help="Email for the admin user"
    )
    parser.add_argument("--password", type=str, required=True, help="Password for the admin user")
    parser.add_argument(
        "--name",
        type=str,
        default="Administrator",
        help="Display name for the admin user",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    logger.info(f"Creating admin user with email: {args.email}")
    success = asyncio.run(create_admin_user(args.email, args.password, args.name))

    if success:
        logger.info("Admin user created or updated successfully.")
        sys.exit(0)
    else:
        logger.error("Failed to create admin user.")
        sys.exit(1)
