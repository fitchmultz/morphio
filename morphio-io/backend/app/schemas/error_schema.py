from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    status: str = Field("error", description="Error status")
    message: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Type of error")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(..., description="Timestamp of the error")

    model_config = ConfigDict(extra="forbid")


class ValidationErrorItem(BaseModel):
    loc: tuple
    msg: str
    type: str

    model_config = ConfigDict(extra="forbid")


class ValidationErrorResponse(ErrorResponse):
    details: list[ValidationErrorItem]

    model_config = ConfigDict(extra="forbid")


class RetryConfig(BaseModel):
    max_retries: int = Field(default=3, ge=1, description="Maximum number of retry attempts")
    delay: int = Field(default=1, ge=0, description="Delay between retries in seconds")

    model_config = ConfigDict(extra="forbid")
