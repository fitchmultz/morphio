"""
Detailed LLM usage tracking model.

Tracks per-call token usage for LLM generations, enabling:
- Cost estimation and billing
- Usage analytics and optimization
- Rate limiting by tokens
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, SoftDeleteMixin

if TYPE_CHECKING:
    from .content import Content
    from .user import User

logger = logging.getLogger(__name__)


class LLMUsageRecord(Base, SoftDeleteMixin):
    """
    Records token usage for individual LLM API calls.

    Captures input/output tokens, model used, and optional cost estimation.
    Can be linked to specific content for attribution.
    """

    __tablename__ = "llm_usage_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    content_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("contents.id"), nullable=True
    )

    # LLM call details
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    model_alias: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # User-facing model name

    # Token counts
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)

    # Cost tracking (optional - populated by cost estimation layer)
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)

    # Context
    operation: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # e.g., "content_generation", "title_generation", "chat"

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", backref="llm_usage_records", lazy="joined")
    content: Mapped["Content | None"] = relationship(
        "Content", backref="llm_usage_records", lazy="joined"
    )

    def __repr__(self) -> str:
        return (
            f"<LLMUsageRecord(id={self.id}, user_id={self.user_id}, "
            f"provider={self.provider}, model={self.model}, "
            f"in={self.input_tokens}, out={self.output_tokens})>"
        )
