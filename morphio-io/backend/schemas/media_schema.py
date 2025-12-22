"""
Compatibility re-exports for legacy import path `schemas.media_schema`.

Avoid wildcard imports to satisfy Ruff (F403) and keep explicit APIs.
"""

from app.schemas.media_schema import (
    JobStatusInfo,
    MediaInput,
    MediaMetadata,
    MediaProcessingInput,
    MediaProcessingRequest,
    MediaProcessingResponse,
    MediaProcessingStatusResponse,
    ProcessedMediaResult,
)
from app.utils.enums import MediaSource, MediaType

__all__ = [
    "MediaProcessingRequest",
    "MediaProcessingInput",
    "MediaProcessingResponse",
    "MediaProcessingStatusResponse",
    "MediaMetadata",
    "ProcessedMediaResult",
    "MediaInput",
    "JobStatusInfo",
    "MediaSource",
    "MediaType",
]
