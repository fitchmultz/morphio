"""
Audio processing types and configuration models.

All types use Pydantic with frozen=True for immutability at API boundaries.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

# Type alias for naming strategy callable
ChunkNamer = Callable[[int, float, float], str]


def default_chunk_namer(index: int, start: float, end: float) -> str:
    """Default naming: chunk_001_0_600.mp3"""
    return f"chunk_{index:03d}_{int(start)}_{int(end)}.mp3"


class AudioChunk(BaseModel):
    """Represents a segment of an audio file."""

    model_config = ConfigDict(frozen=True)

    chunk_path: Path
    start_time: float = Field(ge=0, description="Start time in seconds")
    end_time: float = Field(ge=0, description="End time in seconds")

    @computed_field
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


class ChunkingConfig(BaseModel):
    """Configuration for audio chunking."""

    segment_duration: float = Field(default=600.0, gt=0, description="Chunk duration in seconds")
    overlap_ms: int = Field(
        default=2000, ge=0, description="Overlap between chunks in milliseconds"
    )
    output_format: Literal["mp3", "wav", "m4a", "flac"] = Field(default="mp3")
    copy_codec: bool = Field(
        default=False,
        description="Use stream copy (fast, but input must match output format)",
    )

    @model_validator(mode="after")
    def validate_overlap(self) -> "ChunkingConfig":
        """Ensure overlap is less than segment duration to prevent infinite loops."""
        overlap_sec = self.overlap_ms / 1000.0
        if overlap_sec >= self.segment_duration:
            raise ValueError(
                f"overlap_ms ({self.overlap_ms}) must be less than "
                f"segment_duration ({self.segment_duration}s = {self.segment_duration * 1000}ms)"
            )
        return self


# Whisper transcription types
WhisperModel = Literal["tiny", "base", "small", "medium", "large", "large-v3", "turbo"]
WhisperBackend = Literal["mlx", "faster-whisper", "auto"]
ComputeDevice = Literal["auto", "gpu", "cpu"]


class TranscriptionConfig(BaseModel):
    """Configuration for local Whisper transcription."""

    model: WhisperModel = Field(default="base", description="Whisper model size")
    backend: WhisperBackend = Field(
        default="auto",
        description="Backend: auto-detect, mlx (Apple Silicon), or faster-whisper",
    )
    device: ComputeDevice = Field(
        default="auto", description="Compute device: auto-detect, gpu, or cpu"
    )
    language: str | None = Field(
        default=None, description="ISO language code, None for auto-detect"
    )
    beam_size: int = Field(default=5, ge=1, description="Beam size for decoding")
    word_timestamps: bool = Field(default=True, description="Generate word-level timestamps")


class WordTiming(BaseModel):
    """Word with timing information from transcription."""

    model_config = ConfigDict(frozen=True)

    word: str
    start_time: float = Field(ge=0)
    end_time: float = Field(ge=0)
    confidence: float | None = None


class TranscriptionSegment(BaseModel):
    """A segment from Whisper transcription."""

    model_config = ConfigDict(frozen=True)

    id: int
    text: str
    start_time: float = Field(ge=0)
    end_time: float = Field(ge=0)


class TranscriptionResult(BaseModel):
    """Result from local Whisper transcription."""

    model_config = ConfigDict(frozen=True)

    text: str
    language: str | None = None
    duration: float | None = None
    words: list[WordTiming] = Field(default_factory=list)
    segments: list[TranscriptionSegment] = Field(default_factory=list)
    backend_used: str | None = None  # Which backend was actually used
    device_used: str | None = None  # Which device was used (cpu, cuda, mps)


# Speaker diarization types


class SpeakerSegment(BaseModel):
    """A speaker's segment from diarization."""

    model_config = ConfigDict(frozen=True)

    speaker_id: str
    start_time: float = Field(ge=0)
    end_time: float = Field(ge=0)
    confidence: float | None = None


class SpeakerUtterance(BaseModel):
    """A complete utterance from a speaker with aligned text."""

    model_config = ConfigDict(frozen=True)

    speaker_id: str
    text: str
    start_time: float = Field(ge=0)
    end_time: float = Field(ge=0)
    words: list[WordTiming] = Field(default_factory=list)


class DiarizationResult(BaseModel):
    """Complete diarization output."""

    model_config = ConfigDict(frozen=True)

    segments: list[SpeakerSegment] = Field(default_factory=list)
    num_speakers: int = 0


class TranscriptionSpeakerSegment(BaseModel):
    """Speaker segment with attributed text for output."""

    model_config = ConfigDict(frozen=True)

    speaker_id: str
    start_time: float = Field(ge=0)
    end_time: float = Field(ge=0)
    text: str
