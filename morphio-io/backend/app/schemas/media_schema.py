from typing import Any, Dict, Optional, Union

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, HttpUrl

from ..utils.enums import JobStatus, MediaProcessingStatus, MediaSource, MediaType


class MediaProcessingRequest(BaseModel):
    source: MediaSource
    url: Optional[HttpUrl] = Field(None, description="YouTube URL if source is YouTube")
    template_id: int = Field(..., description="ID of the template to use")
    media_type: MediaType = Field(..., description="Type of media (video or audio)")

    model_config = ConfigDict()


class MediaProcessingInput(BaseModel):
    source: MediaSource
    url: Optional[AnyHttpUrl] = Field(None, description="YouTube URL if source is YouTube")
    file_path: Optional[str] = Field(None, description="Local file path if source is upload")
    template_id: int = Field(..., description="ID of the template to use")
    user_id: int = Field(..., description="ID of the user processing the media")
    media_type: MediaType = Field(..., description="Type of media (video or audio)")
    model_name: Optional[str] = Field(None, description="Name of the model to use for generation")

    # Speaker diarization options
    enable_diarization: bool = Field(
        False, description="Enable speaker diarization to identify multiple speakers"
    )
    min_speakers: Optional[int] = Field(
        None, description="Minimum expected number of speakers (optional hint)"
    )
    max_speakers: Optional[int] = Field(
        None, description="Maximum expected number of speakers (optional hint)"
    )

    model_config = ConfigDict()


class MediaProcessingResponse(BaseModel):
    job_id: str
    status: MediaProcessingStatus
    message: Optional[str] = None

    model_config = ConfigDict()


class MediaProcessingStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: int = Field(default=0, ge=0, le=100)
    message: Optional[str] = None
    result: Optional[Union[str, Dict[str, Any]]] = None
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MediaMetadata(BaseModel):
    title: str
    description: Optional[str] = None
    duration: float
    thumbnail_url: Optional[HttpUrl] = None

    model_config = ConfigDict()


class ProcessedMediaResult(BaseModel):
    media_id: str
    metadata: MediaMetadata
    transcript: str
    generated_content: str

    model_config = ConfigDict()


class MediaInput(BaseModel):
    url: Optional[HttpUrl] = None
    file: Optional[str] = None

    model_config = ConfigDict()


class JobStatusInfo(BaseModel):
    job_id: str
    status: str
    progress: int
    result: Optional[str] = None

    model_config = ConfigDict()
