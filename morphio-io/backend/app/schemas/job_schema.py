from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..utils.enums import JobStatus, ProcessingStage


class JobBase(BaseModel):
    status: JobStatus = Field(default=JobStatus.PENDING)
    job_type: str
    params: Dict[str, Any] = Field(default_factory=dict)


class JobCreate(JobBase):
    user_id: int


class JobUpdate(BaseModel):
    status: Optional[JobStatus] = None
    result: Optional[Dict[str, Any]] = None


class JobInDB(JobBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class JobOut(JobInDB):
    progress: int = Field(default=0, ge=0, le=100)
    message: Optional[str] = None
    stage: Optional[ProcessingStage] = None

    model_config = ConfigDict(from_attributes=True)


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: int = Field(default=0, ge=0, le=100)
    message: Optional[str] = None
    stage: Optional[ProcessingStage] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    user_id: Optional[int] = None
    chosen_model: Optional[str] = None

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)


class JobStatusInfo(BaseModel):
    job_id: str
    status: JobStatus
    progress: int = Field(default=0, ge=0, le=100)
    message: Optional[str] = None
    stage: Optional[ProcessingStage] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    user_id: Optional[int] = None
    chosen_model: Optional[str] = None

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)
