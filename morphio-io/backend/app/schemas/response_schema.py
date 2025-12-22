from datetime import datetime
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, field_serializer

from ..utils.enums import ResponseStatus

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    status: ResponseStatus
    message: str
    data: Optional[T] = None
    timestamp: Optional[datetime] = None

    @field_serializer("timestamp")
    def serialize_datetime(self, dt: datetime, _info):
        return dt.isoformat() if dt else None


class ResponseModel(BaseModel, Generic[T]):
    status: str
    message: str
    data: Optional[T] = None

    @field_serializer("data")
    def serialize_data(self, v: Any, _info):
        if isinstance(v, datetime):
            return v.isoformat()
        return v


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    per_page: int

    model_config = ConfigDict(arbitrary_types_allowed=True)
