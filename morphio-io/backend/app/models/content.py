from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from .base import Base, SoftDeleteMixin, logger

if TYPE_CHECKING:
    from .tag import Tag
    from .comment import Comment
    from .conversation import ContentConversation
    from .user import User
    from .template import Template


class Content(Base, SoftDeleteMixin):
    __tablename__ = "contents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    template_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("templates.id"), nullable=True
    )

    tags: Mapped[list["Tag"]] = relationship(
        "Tag", secondary="content_tags", back_populates="contents", lazy="joined"
    )
    comments: Mapped[list["Comment"]] = relationship(
        "Comment",
        back_populates="content",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    conversations: Mapped[list["ContentConversation"]] = relationship(
        "ContentConversation",
        back_populates="content",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    user: Mapped["User"] = relationship("User", back_populates="contents", lazy="joined")
    template: Mapped["Template | None"] = relationship(
        "Template", back_populates="contents", lazy="joined"
    )

    @hybrid_property
    def comment_count(self) -> int:
        return len(self.comments)

    def increment_view(self):
        self.view_count += 1
        logger.info(f"View count incremented for content {self.id}")

    def __repr__(self):
        return f"<Content(id={self.id}, title='{self.title}')>"
