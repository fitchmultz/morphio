from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, Enum, Integer, String, func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
import bcrypt
from typing import TYPE_CHECKING

from ..utils.enums import UserRole
from .base import Base, SoftDeleteMixin, logger

if TYPE_CHECKING:
    from .content import Content
    from .template import Template
    from .comment import Comment
    from .conversation import ContentConversation
    from .usage import Usage
    from .subscription import Subscription


class User(Base, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # CHANGED HERE: Now default=UserRole.USER means "USER" (uppercase)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER)

    contents: Mapped[list["Content"]] = relationship(
        "Content", back_populates="user", lazy="selectin"
    )
    conversations: Mapped[list["ContentConversation"]] = relationship(
        "ContentConversation", back_populates="user", lazy="selectin"
    )
    templates: Mapped[list["Template"]] = relationship(
        "Template", back_populates="user", lazy="selectin"
    )
    comments: Mapped[list["Comment"]] = relationship(
        "Comment", back_populates="author", lazy="selectin"
    )

    usage_records: Mapped[list["Usage"]] = relationship(
        "Usage", back_populates="user", lazy="selectin"
    )
    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription", back_populates="user", lazy="selectin"
    )

    def set_password(self, password: str) -> None:
        self.hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
            "utf-8"
        )
        logger.info(f"Password set for user {self.id}")

    def check_password(self, password: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), self.hashed_password.encode("utf-8"))
        except Exception:
            return False

    @hybrid_property
    def content_count(self) -> int:
        return len(self.contents)

    @hybrid_property
    def is_admin(self) -> bool:
        return bool(self.role == UserRole.ADMIN)
