"""
Audio processing utilities.

Provides:
- Audio chunking with overlap support
- Local Whisper transcription (MLX, faster-whisper)
- Speaker diarization alignment
"""

from .alignment import (
    align_speakers_to_words,
    find_overlapping_speaker,
    format_diarized_transcript,
    merge_cross_chunk_speakers,
    utterances_to_segments,
)
from .chunking import (
    ChunkingResult,
    audio_chunker,
    chunk_audio,
    cleanup_chunks,
    segment_audio_fast,
)
from .transcription import (
    FasterWhisperBackend,
    MLXWhisperBackend,
    Transcriber,
    WhisperBackendProtocol,
    detect_optimal_backend,
    has_faster_whisper,
    has_mlx_whisper,
    has_nvidia_gpu,
    is_apple_silicon,
    transcribe_audio,
)
from .types import (
    AudioChunk,
    ChunkingConfig,
    ChunkNamer,
    DiarizationResult,
    SpeakerSegment,
    SpeakerUtterance,
    TranscriptionConfig,
    TranscriptionResult,
    TranscriptionSegment,
    TranscriptionSpeakerSegment,
    WordTiming,
    default_chunk_namer,
)

__all__ = [
    # Types
    "AudioChunk",
    "ChunkingConfig",
    "ChunkNamer",
    "ChunkingResult",
    "DiarizationResult",
    "SpeakerSegment",
    "SpeakerUtterance",
    "TranscriptionConfig",
    "TranscriptionResult",
    "TranscriptionSegment",
    "TranscriptionSpeakerSegment",
    "WordTiming",
    "default_chunk_namer",
    # Chunking
    "audio_chunker",
    "chunk_audio",
    "cleanup_chunks",
    "segment_audio_fast",
    # Transcription
    "FasterWhisperBackend",
    "MLXWhisperBackend",
    "Transcriber",
    "WhisperBackendProtocol",
    "detect_optimal_backend",
    "has_faster_whisper",
    "has_mlx_whisper",
    "has_nvidia_gpu",
    "is_apple_silicon",
    "transcribe_audio",
    # Alignment
    "align_speakers_to_words",
    "find_overlapping_speaker",
    "format_diarized_transcript",
    "merge_cross_chunk_speakers",
    "utterances_to_segments",
]
