import json
import logging
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from fastapi.responses import JSONResponse

from ..schemas.response_schema import ApiResponse
from ..utils.enums import ResponseStatus

logger = logging.getLogger(__name__)


def utc_now():
    return datetime.now(UTC)


def create_response(
    status: ResponseStatus,
    message: str,
    data: dict | list | None = None,
    status_code: int = 200,
) -> JSONResponse:
    """Create a standardized JSON response."""
    response = ApiResponse(
        status=status,
        message=message,
        data=data,
        timestamp=utc_now(),
    )
    return JSONResponse(
        content=json.loads(json.dumps(response.model_dump(), cls=CustomJSONEncoder)),
        status_code=status_code,
    )


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for enums and datetimes."""

    def default(self, o: Any) -> Any:
        if isinstance(o, Enum):
            return o.value
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)
