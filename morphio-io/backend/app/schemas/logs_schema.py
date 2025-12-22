from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict

from ..utils.enums import JobStatus


class LogsProcessingResponse(BaseModel):
    job_id: str
    status: str
    message: Optional[str] = None

    model_config = ConfigDict()


class LogsProcessingStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: int = 0
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
