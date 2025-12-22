from __future__ import annotations

from typing import TYPE_CHECKING
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, SoftDeleteMixin

if TYPE_CHECKING:
    from .user import User
    from .content import Content
    from .conversation import ContentConversation


class Template(Base, SoftDeleteMixin):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    template_content: Mapped[str] = mapped_column(Text, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    user: Mapped["User | None"] = relationship("User", back_populates="templates")
    contents: Mapped[list["Content"]] = relationship(
        "Content", back_populates="template", lazy="selectin"
    )
    conversations: Mapped[list["ContentConversation"]] = relationship(
        "ContentConversation",
        back_populates="template",
        lazy="selectin",
    )

    @classmethod
    async def get_user_templates(cls, db: AsyncSession, user_id: int):
        return (await db.execute(select(cls).where(cls.user_id == user_id))).scalars().all()

    @classmethod
    async def get_by_id(cls, db: AsyncSession, template_id: int):
        return await db.get(cls, template_id)

    async def save(self, db: AsyncSession):
        db.add(self)
        await db.commit()
        await db.refresh(self)

    def __repr__(self):
        return f"<Template {self.name}>"
