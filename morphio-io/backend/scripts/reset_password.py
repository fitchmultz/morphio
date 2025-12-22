#!/usr/bin/env python3
"""
Set or reset a user's password (and optionally make them admin).

Usage:
  uv run python -m scripts.reset_password --email you@example.com --password 'NewPass123!' [--admin]
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.user import User
from app.services.security import get_password_hash
from app.utils.enums import UserRole


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def reset_password(email: str, password: str, make_admin: bool) -> None:
    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == email))
        if not user:
            logger.error(f"No user found with email: {email}")
            return

        user.hashed_password = get_password_hash(password)
        if make_admin:
            user.role = UserRole.ADMIN

        await session.commit()
        logger.info(
            f"Password updated for {email}{' and role set to ADMIN' if make_admin else ''}."
        )


def main():
    parser = argparse.ArgumentParser(description="Reset a user's password")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--admin", action="store_true")
    args = parser.parse_args()

    asyncio.run(reset_password(args.email, args.password, args.admin))


if __name__ == "__main__":
    main()
