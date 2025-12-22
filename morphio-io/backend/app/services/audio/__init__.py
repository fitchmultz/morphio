"""Audio processing services."""

from .chunking import chunk_audio_file, cleanup_chunks
from .pipeline import (
    should_use_diarization,
    transcribe_chunks_standard,
    transcribe_with_diarization,
)
from .processing import (
    enqueue_audio_processing,
    get_audio_processing_status,
    transcribe_and_generate_audio,
)
from .transcription import (
    transcribe_audio,
    transcribe_audio_chunk,
    transcribe_audio_local,
)

__all__ = [
    # Chunking
    "chunk_audio_file",
    "cleanup_chunks",
    # Pipeline
    "should_use_diarization",
    "transcribe_chunks_standard",
    "transcribe_with_diarization",
    # Processing (orchestration)
    "enqueue_audio_processing",
    "get_audio_processing_status",
    "transcribe_and_generate_audio",
    # Transcription
    "transcribe_audio",
    "transcribe_audio_chunk",
    "transcribe_audio_local",
]
