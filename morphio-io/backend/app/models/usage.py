from __future__ import annotations
import logging
from typing import TYPE_CHECKING

from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..utils.enums import UsageType
from .base import Base, SoftDeleteMixin

if TYPE_CHECKING:
    from .user import User

logger = logging.getLogger(__name__)


class Usage(Base, SoftDeleteMixin):
    __tablename__ = "usages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    # usage_type & credits for plan usage
    usage_type: Mapped[str] = mapped_column(String, nullable=False, default=UsageType.OTHER.value)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    usage_credits: Mapped[int] = mapped_column(Integer, default=0)

    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="usage_records", lazy="joined")

    def increment(self):
        """
        Increment usage_count by 1 and usage_credits by the usage weight in usage_service.
        """
        self.usage_count += 1
        logger.debug(f"Usage incremented to {self.usage_count}")

    @hybrid_property
    def usage_calls(self) -> int:
        """
        Synonym for usage_count, helps clarity in admin pages.
        """
        return self.usage_count

    @hybrid_property
    def usage_points(self) -> int:
        """
        Synonym for usage_credits, to reflect total cost or "points" consumed.
        """
        return self.usage_credits

    def __repr__(self):
        return (
            f"<Usage(id={self.id}, user_id={self.user_id}, "
            f"usage_type={self.usage_type}, usage_count={self.usage_count}, "
            f"credits={self.usage_credits})>"
        )
