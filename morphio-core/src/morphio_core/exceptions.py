"""
Library exception hierarchy - NO HTTP STATUS CODES.

All exceptions are library-specific. The consuming application
(e.g., morphio-io) maps these to HTTP responses at the boundary.
"""


class MorphioCoreError(Exception):
    """Base exception for morphio-core library."""

    pass


# Media exceptions
class MediaError(MorphioCoreError):
    """Base for media processing errors."""

    pass


class FFmpegError(MediaError):
    """FFmpeg command failed."""

    def __init__(
        self,
        message: str,
        command: list[str] | None = None,
        stderr: str = "",
    ):
        self.message = message
        self.command = command or []
        self.stderr = stderr
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        parts = [self.message]
        if self.command:
            parts.append(f"Command: {' '.join(self.command)}")
        if self.stderr:
            parts.append(f"Stderr: {self.stderr}")
        return "\n".join(parts)


# Audio exceptions
class AudioProcessingError(MediaError):
    """Base for audio processing errors."""

    pass


class AudioChunkingError(AudioProcessingError):
    """Audio chunking failed."""

    pass


class TranscriptionError(AudioProcessingError):
    """Transcription failed."""

    pass


class BackendNotAvailableError(TranscriptionError):
    """Requested Whisper backend is not installed or not supported on this platform."""

    pass


class SpeakerAlignmentError(AudioProcessingError):
    """Speaker alignment failed."""

    pass


# LLM exceptions
class LLMError(MorphioCoreError):
    """Base for LLM-related errors."""

    pass


class ProviderError(LLMError):
    """Provider-specific error with context."""

    def __init__(
        self,
        message: str,
        provider: str,
        model: str | None = None,
        original_error: Exception | None = None,
    ):
        self.message = message
        self.provider = provider
        self.model = model
        self.original_error = original_error
        super().__init__(message)


class LLMProviderError(LLMError):
    """Simple LLM provider error (use when provider/model context not needed)."""

    pass


class OptionalDependencyError(LLMProviderError):
    """SDK or optional dependency is not installed.

    Provides actionable error messages with the exact install command.
    """

    def __init__(self, package: str, extra: str, pip_package: str | None = None):
        """Create an optional dependency error.

        Args:
            package: Human-readable package name (e.g., "OpenAI SDK")
            extra: The morphio-core extra to install (e.g., "llm", "llm-openai")
            pip_package: Pip package name if different from extra (e.g., "openai")
        """
        self.package = package
        self.extra = extra
        self.pip_package = pip_package or extra

        message = (
            f"{package} not installed. "
            f"Install with: uv add morphio-core[{extra}] or pip install {self.pip_package}"
        )
        super().__init__(message)


class ProviderNotConfiguredError(LLMError):
    """Requested provider is not configured."""

    pass


class APIKeyMissingError(LLMError):
    """Required API key is missing."""

    pass


# Security exceptions
class SecurityError(MorphioCoreError):
    """Base for security-related errors."""

    pass


class SSRFBlockedError(SecurityError):
    """URL blocked due to SSRF protection."""

    pass


# Video exceptions
class VideoProcessingError(MediaError):
    """Base for video processing errors."""

    pass


class UnsupportedURLError(VideoProcessingError):
    """URL format not supported."""

    pass


class DownloadError(VideoProcessingError):
    """Video download failed."""

    pass
