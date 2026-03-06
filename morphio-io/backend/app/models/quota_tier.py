"""Purpose: Define quota-tier assignment records used for usage policies.
Responsibilities: Store tier/status data that informs monthly credit limits.
Scope: SQLAlchemy ORM mapping for internal quota-tier assignment records.
Usage: Queried by usage tracking and user credit summary endpoints.
Invariants/Assumptions: The historical database table name remains `subscriptions` for migration stability, even though the app surface now speaks in quota-tier terms.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, SoftDeleteMixin

if TYPE_CHECKING:
    from .user import User

logger = logging.getLogger(__name__)


class QuotaTierName(Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class QuotaTierStatus(Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class QuotaTierAssignment(Base, SoftDeleteMixin):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    # Preserve the historical `plan` column name for migrated databases.
    tier: Mapped[str] = mapped_column("plan", String, default=QuotaTierName.FREE.value)
    status: Mapped[str] = mapped_column(String, default=QuotaTierStatus.ACTIVE.value)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(
        "User", back_populates="quota_tier_assignments", lazy="joined"
    )

    def __repr__(self):
        return (
            f"<QuotaTierAssignment id={self.id} user_id={self.user_id} "
            f"tier={self.tier} status={self.status}>"
        )
