"""Purpose: Adapt morphio-core audio APIs for morphio-io backend workflows.
Responsibilities: Validate transcription options, translate types, and normalize core exceptions.
Scope: Backend adapter layer between morphio-io schemas and morphio-core audio primitives.
Usage: Imported by backend audio services for chunking and local transcription.
Invariants/Assumptions: Whisper model names are validated before reaching morphio-core.
"""

import asyncio
from pathlib import Path
from typing import Final, List, Tuple

from morphio_core.audio import chunking as core_chunking
from morphio_core.audio import transcription as core_transcription
from morphio_core.audio import types as core_types
from morphio_core.exceptions import AudioChunkingError, TranscriptionError

from ..schemas.audio_schema import (
    AudioChunk,
    AudioProcessingInput,
    AudioProcessingResult,
)
from ..schemas.diarization_schema import WordTiming
from ..utils.error_handlers import ApplicationException


# --- Type Conversion Helpers ---


def _to_io_audio_chunk(core_chunk: core_types.AudioChunk) -> AudioChunk:
    """Convert morphio-core AudioChunk to morphio-io AudioChunk."""
    return AudioChunk(
        chunk_path=str(core_chunk.chunk_path),
        start_time=core_chunk.start_time,
        end_time=core_chunk.end_time,
    )


def _to_io_word_timing(core_word: core_types.WordTiming) -> WordTiming:
    """Convert morphio-core WordTiming to morphio-io WordTiming."""
    return WordTiming(
        word=core_word.word,
        start_time=core_word.start_time,
        end_time=core_word.end_time,
        confidence=core_word.confidence,
    )


# --- Audio Chunking Functions ---


async def probe_audio_duration(file_path: str) -> float:
    """
    Get audio duration using ffprobe.

    Args:
        file_path: Path to the audio file

    Returns:
        Duration in seconds

    Raises:
        ApplicationException: If probing fails
    """
    from morphio_core.media.ffmpeg import probe_duration

    try:
        return await probe_duration(Path(file_path))
    except Exception as e:
        raise ApplicationException(
            message=f"ffprobe failed: {str(e)}",
            status_code=500,
        ) from e


async def segment_audio_fast(
    input_file: str,
    output_dir: str,
    segment_duration: int = 600,
) -> List[AudioChunk]:
    """
    Fast audio segmentation using stream copy (no re-encoding).

    This is faster but doesn't support overlap and cuts may not be frame-precise.

    Args:
        input_file: Path to input audio file
        output_dir: Directory for output segments
        segment_duration: Segment length in seconds

    Returns:
        List of AudioChunk with timing info

    Raises:
        ApplicationException: If segmentation fails
    """
    try:
        result = await core_chunking.segment_audio_fast(
            input_path=input_file,
            output_dir=output_dir,
            segment_duration=segment_duration,
        )
        return [_to_io_audio_chunk(c) for c in result.chunks]
    except AudioChunkingError as e:
        raise ApplicationException(
            message=f"ffmpeg segmentation failed: {str(e)}",
            status_code=500,
        ) from e


async def segment_audio_with_overlap(
    input_file: str,
    output_dir: str,
    chunk_duration: float = 600.0,
    overlap_ms: int = 2000,
    total_duration: float | None = None,
) -> List[AudioChunk]:
    """
    Segment audio with overlap for transcription continuity.

    Re-encodes to MP3 to ensure precise cuts.

    Args:
        input_file: Path to input audio file
        output_dir: Directory for output segments
        chunk_duration: Segment length in seconds
        overlap_ms: Overlap between segments in milliseconds
        total_duration: Optional pre-computed total duration

    Returns:
        List of AudioChunk with timing info

    Raises:
        ApplicationException: If segmentation fails
    """
    try:
        config = core_types.ChunkingConfig(
            segment_duration=chunk_duration,
            overlap_ms=overlap_ms,
            output_format="mp3",
            copy_codec=False,  # Re-encode for precise cuts
        )
        result = await core_chunking.chunk_audio(
            input_path=input_file,
            output_dir=output_dir,
            config=config,
        )
        return [_to_io_audio_chunk(c) for c in result.chunks]
    except AudioChunkingError as e:
        raise ApplicationException(
            message=f"ffmpeg chunking failed: {str(e)}",
            status_code=500,
        ) from e


async def chunk_audio_file(input_data: AudioProcessingInput) -> AudioProcessingResult:
    """
    Chunk audio file using ffmpeg.

    Tries fast path first (stream copy), falls back to overlap method.

    Args:
        input_data: Processing input with file path and configuration

    Returns:
        AudioProcessingResult with chunks and metadata

    Raises:
        ApplicationException: If chunking fails
    """
    import os

    original_file = input_data.file_path
    if not os.path.exists(original_file):
        raise ApplicationException(f"File not found: {original_file}", status_code=404)

    try:
        total_duration = await probe_audio_duration(original_file)
    except Exception as e:
        raise ApplicationException(
            message=f"Failed to get audio duration: {str(e)}",
            status_code=500,
        ) from e

    # Try fast path first
    try:
        chunks = await segment_audio_fast(
            original_file,
            input_data.output_directory,
            segment_duration=600,
        )
        if chunks:
            return AudioProcessingResult(
                original_file=original_file,
                processed_file=original_file,
                chunks=chunks,
                total_duration=total_duration,
            )
    except ApplicationException:
        pass  # Fall through to overlap method

    # Fallback to overlap method
    chunks = await segment_audio_with_overlap(
        original_file,
        input_data.output_directory,
        chunk_duration=600.0,
        overlap_ms=input_data.overlap_ms,
        total_duration=total_duration,
    )

    return AudioProcessingResult(
        original_file=original_file,
        processed_file=original_file,
        chunks=chunks,
        total_duration=total_duration,
    )


async def cleanup_chunks(chunk_paths: List[str]) -> None:
    """
    Clean up temporary chunk files.

    Args:
        chunk_paths: List of file paths to remove
    """
    import contextlib
    import os

    for cp in chunk_paths:
        with contextlib.suppress(OSError):
            os.remove(cp)


# --- Transcription Functions ---


_VALID_WHISPER_MODELS: Final[dict[str, core_types.WhisperModel]] = {
    "tiny": "tiny",
    "base": "base",
    "small": "small",
    "medium": "medium",
    "large": "large",
    "large-v3": "large-v3",
    "turbo": "turbo",
}


def _resolve_whisper_model(model_name: str) -> core_types.WhisperModel:
    """Return a validated Whisper model name for morphio-core."""
    resolved_model = _VALID_WHISPER_MODELS.get(model_name)
    if resolved_model is None:
        valid_models = ", ".join(_VALID_WHISPER_MODELS)
        raise ApplicationException(
            message=f"Unsupported Whisper model '{model_name}'. Expected one of: {valid_models}",
            status_code=400,
        )
    return resolved_model


def _create_transcriber(
    model_name: str = "small",
    word_timestamps: bool = False,
) -> core_transcription.Transcriber:
    """Create a configured Transcriber instance."""
    config = core_types.TranscriptionConfig(
        model=_resolve_whisper_model(model_name),
        backend="auto",
        device="auto",
        word_timestamps=word_timestamps,
    )
    return core_transcription.Transcriber(config=config)


async def transcribe_local(
    file_path: str,
    model_name: str = "small",
) -> Tuple[str, float | None]:
    """
    Transcribe audio file using local Whisper model.

    Uses morphio-core's Transcriber which auto-selects the best backend:
    - Apple Silicon -> MLX Whisper (Metal GPU)
    - NVIDIA GPU -> faster-whisper (CUDA)
    - CPU fallback -> faster-whisper

    Args:
        file_path: Path to the audio file
        model_name: Whisper model name (default: "small")

    Returns:
        Tuple of (transcribed text, confidence score or None)

    Raises:
        ApplicationException: If transcription fails
    """
    try:
        transcriber = _create_transcriber(model_name=model_name, word_timestamps=False)
        # Run synchronous transcribe in thread pool
        result = await asyncio.to_thread(transcriber.transcribe, file_path)
        # morphio-core doesn't provide confidence in same way, return None
        return result.text, None
    except TranscriptionError as e:
        raise ApplicationException(
            message=f"Transcription failed: {str(e)}",
            status_code=500,
        ) from e


async def transcribe_with_word_timestamps(
    file_path: str,
    model_name: str = "small",
) -> Tuple[str, List[WordTiming]]:
    """
    Transcribe audio file with word-level timestamps for diarization alignment.

    Args:
        file_path: Path to the audio file
        model_name: Whisper model name (default: "small")

    Returns:
        Tuple of (transcribed text, list of word timings)

    Raises:
        ApplicationException: If transcription fails
    """
    try:
        transcriber = _create_transcriber(model_name=model_name, word_timestamps=True)
        result = await asyncio.to_thread(transcriber.transcribe, file_path)
        word_timings = [_to_io_word_timing(w) for w in result.words]
        return result.text, word_timings
    except TranscriptionError as e:
        raise ApplicationException(
            message=f"Transcription with timestamps failed: {str(e)}",
            status_code=500,
        ) from e


__all__ = [
    # Chunking
    "probe_audio_duration",
    "segment_audio_fast",
    "segment_audio_with_overlap",
    "chunk_audio_file",
    "cleanup_chunks",
    # Transcription
    "transcribe_local",
    "transcribe_with_word_timestamps",
]
