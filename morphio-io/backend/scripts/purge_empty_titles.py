import asyncio
import os
import sys

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from app.database import engine
from app.models.content import Content
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession


async def purge_contents_with_no_title():
    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(Content).where(or_(Content.title.is_(None), Content.title == ""))
        )
        contents_to_delete = result.unique().scalars().all()

        for item in contents_to_delete:
            await session.delete(item)
        await session.commit()


if __name__ == "__main__":
    asyncio.run(purge_contents_with_no_title())
