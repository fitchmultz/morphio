from typing import List, Optional

from pydantic import BaseModel, Field

from ..utils.enums import TranscriptionSource, TranscriptionStatus
from .diarization_schema import TranscriptionSpeakerSegment


class AudioProcessingInput(BaseModel):
    file_path: str = Field(..., description="Path to the audio file")
    max_file_size_MB: int = Field(24, description="Maximum file size in MB")
    overlap_ms: int = Field(2000, description="Overlap in milliseconds for audio chunks")
    output_directory: str = Field("uploads", description="Directory to save processed audio")


class AudioChunk(BaseModel):
    chunk_path: str = Field(..., description="Path to the audio chunk file")
    start_time: float = Field(..., description="Start time of the chunk in seconds")
    end_time: float = Field(..., description="End time of the chunk in seconds")


class AudioProcessingResult(BaseModel):
    original_file: str = Field(..., description="Path to the original audio file")
    processed_file: str = Field(..., description="Path to the processed audio file")
    chunks: List[AudioChunk] = Field(default_factory=list, description="List of audio chunks")
    total_duration: float = Field(..., description="Total duration of the audio in seconds")


class TranscriptionResult(BaseModel):
    text: str = Field(..., description="Transcribed text")
    confidence: Optional[float] = Field(None, description="Confidence score of the transcription")
    status: TranscriptionStatus = Field(default=TranscriptionStatus.COMPLETED)
    source: TranscriptionSource = Field(
        default=TranscriptionSource.WHISPER, description="Source of transcription"
    )
    error: Optional[str] = Field(None, description="Error message if transcription failed")
    metadata: Optional[dict] = Field(default_factory=dict, description="Additional metadata")

    # Speaker diarization fields (populated when diarization is enabled)
    speakers: Optional[List[TranscriptionSpeakerSegment]] = Field(
        default=None, description="Speaker segments with attributed text (when diarization enabled)"
    )
    num_speakers: Optional[int] = Field(
        default=None, description="Number of unique speakers detected"
    )
    diarization_enabled: bool = Field(
        default=False, description="Whether speaker diarization was performed"
    )
