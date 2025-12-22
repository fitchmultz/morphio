from __future__ import annotations

import logging

from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, declarative_base, declared_attr, mapped_column

from ..utils.response_utils import utc_now

Base = declarative_base()
logger = logging.getLogger(__name__)


class SoftDeleteMixin:
    @declared_attr
    def deleted_at(cls) -> Mapped[datetime | None]:
        return mapped_column(DateTime(timezone=True), nullable=True)

    def soft_delete(self):
        self.deleted_at = utc_now()
        obj_id = getattr(self, "id", None)
        logger.info(f"{self.__class__.__name__} {obj_id} soft deleted")

    def restore(self):
        self.deleted_at = None
        obj_id = getattr(self, "id", None)
        logger.info(f"{self.__class__.__name__} {obj_id} restored")

    @classmethod
    def not_deleted(cls):
        return cls.deleted_at.is_(None)
