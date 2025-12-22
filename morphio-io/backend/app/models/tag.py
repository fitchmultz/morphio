from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, Integer, String, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, logger

if TYPE_CHECKING:
    from .content import Content


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    contents: Mapped[list["Content"]] = relationship(
        "Content", secondary="content_tags", back_populates="tags", lazy="selectin"
    )

    @classmethod
    async def get_or_create(cls, name: str, session: AsyncSession):
        """
        Concurrency-safe get_or_create. If multiple sessions try at the same time, we handle IntegrityError.
        """
        try:
            tag = await session.scalar(select(cls).filter_by(name=name))
            if not tag:
                tag = cls(name=name)
                session.add(tag)
                await session.commit()
                logger.info(f"New tag created: {name}")
            return tag
        except IntegrityError:
            await session.rollback()
            # Attempt to get existing tag again
            existing_tag = await session.scalar(select(cls).filter_by(name=name))
            if existing_tag:
                return existing_tag
            raise

    def __repr__(self):
        return f"<Tag {self.name}>"


class ContentTag(Base):
    __tablename__ = "content_tags"

    content_id: Mapped[int] = mapped_column(Integer, ForeignKey("contents.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(Integer, ForeignKey("tags.id"), primary_key=True)
