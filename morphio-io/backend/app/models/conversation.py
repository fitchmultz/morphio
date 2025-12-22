from __future__ import annotations

from datetime import datetime
from typing import Any, TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, SoftDeleteMixin, logger

if TYPE_CHECKING:
    from .content import Content
    from .template import Template
    from .user import User


class ContentConversation(Base, SoftDeleteMixin):
    __tablename__ = "content_conversations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4()), index=True
    )
    content_id: Mapped[int] = mapped_column(
        ForeignKey("contents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    template_id: Mapped[int | None] = mapped_column(ForeignKey("templates.id"), nullable=True)
    template_used: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    context_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    parent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("content_conversations.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    content: Mapped["Content"] = relationship("Content", back_populates="conversations")
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    template: Mapped["Template | None"] = relationship("Template", back_populates="conversations")
    messages: Mapped[list["ConversationMessage"]] = relationship(
        "ConversationMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.created_at",
        lazy="selectin",
    )
    parent: Mapped["ContentConversation | None"] = relationship(
        "ContentConversation",
        remote_side="ContentConversation.id",
        back_populates="branches",
        lazy="selectin",
        uselist=False,
    )
    branches: Mapped[list["ContentConversation"]] = relationship(
        "ContentConversation",
        back_populates="parent",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover - repr for debugging only
        return ("<ContentConversation id={0} content_id={1} user_id={2} model='{3}'>").format(
            self.id, self.content_id, self.user_id, self.model
        )

    def log_branch_creation(self, branch_id: str) -> None:
        logger.info(
            "Conversation %s branched to %s for content %s",
            self.id,
            branch_id,
            self.content_id,
        )


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("content_conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation: Mapped["ContentConversation"] = relationship(
        "ContentConversation", back_populates="messages"
    )

    def __repr__(self) -> str:  # pragma: no cover - repr for debugging only
        return f"<ConversationMessage id={self.id} role={self.role}>"
