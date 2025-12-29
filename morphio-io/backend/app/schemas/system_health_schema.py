from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class HealthComponentStatus(str, Enum):
    OK = "ok"
    ERROR = "error"
    SKIPPED = "skipped"


class SystemHealthStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    DOWN = "down"


class HealthComponentOut(BaseModel):
    status: HealthComponentStatus
    latency_ms: Optional[int] = Field(
        default=None, description="Elapsed time for the component check in milliseconds."
    )
    detail: Optional[str] = Field(
        default=None, description="Short, non-sensitive diagnostic detail for the component."
    )


class SystemHealthOut(BaseModel):
    overall_status: SystemHealthStatus
    components: dict[str, HealthComponentOut]
