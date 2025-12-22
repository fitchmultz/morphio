"""
morphio-core: Reusable Python library for audio processing, LLM orchestration, and security utilities.

This library provides project-agnostic functionality for:
- Audio chunking, transcription, and speaker alignment
- Multi-provider LLM routing (OpenAI, Anthropic, Gemini)
- Security utilities (URL validation, content anonymization)
- Video processing and YouTube integration

All configuration is explicit - no global settings. All exceptions are library-specific
without HTTP status codes, making this suitable for any Python project.
"""

from morphio_core.exceptions import (
    APIKeyMissingError,
    AudioChunkingError,
    AudioProcessingError,
    BackendNotAvailableError,
    DownloadError,
    FFmpegError,
    LLMError,
    LLMProviderError,
    MediaError,
    MorphioCoreError,
    ProviderError,
    ProviderNotConfiguredError,
    SecurityError,
    SpeakerAlignmentError,
    SSRFBlockedError,
    TranscriptionError,
    UnsupportedURLError,
    VideoProcessingError,
)

__version__ = "0.1.0"

__all__ = [
    # Exceptions
    "MorphioCoreError",
    "MediaError",
    "FFmpegError",
    "AudioProcessingError",
    "AudioChunkingError",
    "TranscriptionError",
    "BackendNotAvailableError",
    "SpeakerAlignmentError",
    "LLMError",
    "LLMProviderError",
    "ProviderError",
    "ProviderNotConfiguredError",
    "APIKeyMissingError",
    "SecurityError",
    "SSRFBlockedError",
    "VideoProcessingError",
    "UnsupportedURLError",
    "DownloadError",
]
