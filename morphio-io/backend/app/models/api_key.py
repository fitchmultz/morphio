"""API Key model for programmatic access."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, SoftDeleteMixin

if TYPE_CHECKING:
    from .user import User


def generate_api_key() -> str:
    """Generate a secure random API key."""
    return f"mio_{secrets.token_urlsafe(32)}"


def hash_api_key(key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()


class APIKey(Base, SoftDeleteMixin):
    """API key for programmatic access to the API."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    hashed_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    key_prefix: Mapped[str] = mapped_column(
        String(12), nullable=False
    )  # First 8 chars for identification
    scopes: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Comma-separated list of scopes
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="api_keys", lazy="joined")

    @classmethod
    def create_key(
        cls, user_id: int, name: str, scopes: list[str] | None = None
    ) -> tuple["APIKey", str]:
        """Create a new API key and return both the model and plaintext key.

        Args:
            user_id: The user ID to associate with the key
            name: A friendly name for the key
            scopes: Optional list of permission scopes

        Returns:
            Tuple of (APIKey instance, plaintext key)
            Note: The plaintext key is only available at creation time
        """
        plaintext_key = generate_api_key()
        hashed = hash_api_key(plaintext_key)
        key_prefix = plaintext_key[:12]  # "mio_" + first 8 chars of token

        api_key = cls(
            user_id=user_id,
            name=name,
            hashed_key=hashed,
            key_prefix=key_prefix,
            scopes=",".join(scopes) if scopes else None,
        )

        return api_key, plaintext_key

    @classmethod
    def verify_key(cls, plaintext_key: str) -> str:
        """Hash a plaintext key for lookup."""
        return hash_api_key(plaintext_key)

    def get_scopes(self) -> list[str]:
        """Get the list of scopes for this key."""
        if not self.scopes:
            return []
        return [s.strip() for s in self.scopes.split(",") if s.strip()]

    def __repr__(self) -> str:
        return f"<APIKey id={self.id} name={self.name} prefix={self.key_prefix}...>"
