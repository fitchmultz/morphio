"""
Speaker diarization schemas for multi-speaker transcription.

These schemas support the hybrid MLX Whisper + pyannote-audio pipeline
for identifying and attributing speech to multiple speakers.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class WordTiming(BaseModel):
    """A word with its timing information from Whisper transcription."""

    word: str = Field(..., description="The transcribed word")
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")
    confidence: Optional[float] = Field(None, description="Word-level confidence score")


class SpeakerSegment(BaseModel):
    """A segment of audio attributed to a single speaker from pyannote diarization."""

    speaker_id: str = Field(..., description="Speaker identifier (e.g., 'SPEAKER_00')")
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")
    confidence: Optional[float] = Field(None, description="Diarization confidence score")


class SpeakerUtterance(BaseModel):
    """A complete utterance from a speaker with aligned text."""

    speaker_id: str = Field(..., description="Speaker identifier")
    text: str = Field(..., description="Transcribed text for this utterance")
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")
    words: List[WordTiming] = Field(default_factory=list, description="Word-level timings")


class DiarizationResult(BaseModel):
    """Complete diarization output from pyannote-audio."""

    segments: List[SpeakerSegment] = Field(
        default_factory=list, description="List of speaker segments"
    )
    num_speakers: int = Field(0, description="Number of unique speakers detected")
    processing_time_seconds: float = Field(0.0, description="Time taken for diarization")
    model_name: str = Field(
        "pyannote/speaker-diarization-3.1", description="Model used for diarization"
    )


class TranscriptionSpeakerSegment(BaseModel):
    """Speaker segment with attributed text for API response."""

    speaker_id: str = Field(..., description="Speaker identifier (e.g., 'SPEAKER_00')")
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")
    text: str = Field(..., description="Transcribed text attributed to this speaker")


# --- Video Summarization Schemas ---


class KeyFrame(BaseModel):
    """Extracted video frame for summary."""

    timestamp: float = Field(..., description="Timestamp in seconds")
    scene_index: int = Field(..., description="Scene index from detection")
    frame_path: str = Field(..., description="Path to extracted JPEG")


class ChapterSummary(BaseModel):
    """Summary of a video chapter/section."""

    title: str = Field(..., description="Chapter title")
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")
    summary: str = Field(..., description="Chapter summary text")
    key_points: List[str] = Field(default_factory=list, description="Key points from chapter")
    keyframe: Optional[KeyFrame] = Field(None, description="Representative frame for chapter")
    speakers: List[str] = Field(default_factory=list, description="Speakers in this chapter")


class VideoSummary(BaseModel):
    """Complete video summary with chapters."""

    title: str = Field(..., description="Video title")
    source: str = Field(..., description="Source URL or file path")
    duration: float = Field(..., description="Video duration in seconds")
    executive_summary: str = Field(..., description="High-level summary of the video")
    chapters: List[ChapterSummary] = Field(
        default_factory=list, description="Chapter-by-chapter breakdown"
    )
    num_speakers: int = Field(0, description="Number of speakers detected")
    keyframes: List[KeyFrame] = Field(default_factory=list, description="All extracted keyframes")
