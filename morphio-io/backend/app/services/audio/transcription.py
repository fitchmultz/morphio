"""
Audio transcription service with caching and concurrency control.

Uses morphio-core's Transcriber for the actual transcription work,
while this module provides:
- Caching via cache_utils
- Concurrency control via semaphore
- Remote ML worker fallback
- Application-specific result types
"""

import asyncio
import logging
import platform
import sys
from typing import List, Optional, Tuple

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ...adapters.audio import transcribe_local, transcribe_with_word_timestamps
from ...config import settings
from ...schemas.audio_schema import (
    TranscriptionResult,
    TranscriptionSource,
    TranscriptionStatus,
)
from ...schemas.diarization_schema import WordTiming
from ...utils.cache_utils import (
    cache_transcription,
    get_cached_transcription,
    invalidate_cache,
)
from ...utils.file_utils import compute_file_hash

logger = logging.getLogger(__name__)


# Limit concurrent transcriptions to avoid GPU/MLX contention
try:
    import multiprocessing as _mp

    _cpu = _mp.cpu_count() or 4
except Exception:
    _cpu = 4

_SEM_SIZE = (
    1 if (sys.platform == "darwin" and platform.machine() in {"arm64", "aarch64"}) else min(2, _cpu)
)
_TRANSCRIBE_SEM = asyncio.Semaphore(_SEM_SIZE)


async def transcribe_audio_local(file_path: str, model_name: str = "small") -> TranscriptionResult:
    """
    Transcribe audio file using local Whisper model.

    Uses morphio-core's hardware-optimized backend selection:
    - Apple Silicon -> MLX Whisper (Metal GPU)
    - NVIDIA GPU -> faster-whisper (CUDA)
    - CPU fallback -> faster-whisper

    Args:
        file_path: Path to the audio file
        model_name: Whisper model name (default: "small")

    Returns:
        TranscriptionResult with text and status
    """
    try:
        text, confidence = await transcribe_local(file_path, model_name)

        if not text:
            logger.warning("Transcription result is empty or invalid")
            return TranscriptionResult(
                text="",
                confidence=None,
                status=TranscriptionStatus.FAILED,
                source=TranscriptionSource.WHISPER,
                error="Empty or invalid transcription result",
            )

        return TranscriptionResult(
            text=text,
            confidence=confidence,
            status=TranscriptionStatus.COMPLETED,
            source=TranscriptionSource.WHISPER,
            error=None,
        )

    except MemoryError:
        # Let MemoryError bubble up for @retry to handle
        raise
    except Exception as e:
        logger.error(f"Error in local transcription: {str(e)}", exc_info=True)
        return TranscriptionResult(
            text="",
            confidence=None,
            status=TranscriptionStatus.FAILED,
            source=TranscriptionSource.WHISPER,
            error=str(e),
        )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
async def transcribe_audio(
    file_path: str,
    source: TranscriptionSource = TranscriptionSource.WHISPER,
    identifier: Optional[str] = None,
) -> TranscriptionResult:
    """
    Transcribe audio file with caching.

    Checks cache first, then tries remote ML worker if configured,
    finally falls back to local transcription.

    Args:
        file_path: Path to the audio file
        source: Source identifier for caching
        identifier: Optional cache identifier (defaults to file hash)

    Returns:
        TranscriptionResult with text and status
    """
    try:
        cache_id = identifier or await compute_file_hash(file_path)
        cached_result = await get_cached_transcription(cache_id, source)
        if cached_result and cached_result.status == TranscriptionStatus.COMPLETED:
            logger.info(f"Using cached transcription for {cache_id}")
            return cached_result

        # Prefer external ML worker if configured
        if settings.WORKER_ML_URL:
            try:
                timeout = httpx.Timeout(settings.SERVICE_TIMEOUT)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    with open(file_path, "rb") as f:
                        files = {"file": (file_path.split("/")[-1], f, "audio/mpeg")}
                        resp = await client.post(
                            f"{settings.WORKER_ML_URL.rstrip('/')}/transcribe",
                            files=files,
                        )
                    resp.raise_for_status()
                    data = resp.json()
                    text = data.get("text", "")
                    if not text:
                        raise ValueError("Empty transcription from worker")
                    result = TranscriptionResult(
                        text=text,
                        confidence=data.get("confidence"),
                        status=TranscriptionStatus.COMPLETED,
                        source=source,
                        error=None,
                    )
            except Exception as e:
                logger.error(f"Remote ML worker error: {e}")
                # Fallback to local if available
                async with _TRANSCRIBE_SEM:
                    result = await transcribe_audio_local(file_path, settings.WHISPER_MODEL)
        else:
            async with _TRANSCRIBE_SEM:
                result = await transcribe_audio_local(file_path, settings.WHISPER_MODEL)

        if result.status == TranscriptionStatus.COMPLETED and result.text:
            await cache_transcription(cache_id, result, source)
            return result
        else:
            await invalidate_cache(f"{source.value}_transcription", cache_id)
            logger.error(f"Transcription failed for {file_path}: {result.error}")
            return result
    except Exception as e:
        logger.error(f"Error in transcribe_audio: {e}", exc_info=True)
        error_result = TranscriptionResult(
            text="",
            confidence=None,
            status=TranscriptionStatus.FAILED,
            source=source,
            error=str(e),
        )
        if identifier:
            await invalidate_cache(f"{source.value}_transcription", identifier)
        return error_result


async def transcribe_audio_chunk(audio_chunk: str) -> str:
    """
    Transcribe a chunked audio file.

    Args:
        audio_chunk: Path to the audio chunk file

    Returns:
        Transcribed text, or empty string on failure
    """
    try:
        logger.debug(f"Transcribing chunk: {audio_chunk}")
        result = await transcribe_audio(audio_chunk)
        if not result or not result.text:
            logger.warning(f"Empty transcription for chunk: {audio_chunk}")
        return result.text if (result and result.text) else ""
    except Exception as e:
        logger.error(f"Error transcribing chunk {audio_chunk}: {str(e)}")
        return ""


async def _transcribe_with_word_timestamps_impl(
    file_path: str,
    model_name: str = "small",
) -> Tuple[str, List[WordTiming]]:
    """
    Internal implementation that calls the adapter.

    Args:
        file_path: Path to the audio file
        model_name: Whisper model name

    Returns:
        Tuple of (transcribed text, list of word timings)
    """
    try:
        text, word_timings = await transcribe_with_word_timestamps(file_path, model_name)
        logger.info(f"Transcribed {len(word_timings)} words with timestamps")
        return text, word_timings
    except Exception as e:
        logger.error(f"Error in transcription with word timestamps: {e}", exc_info=True)
        return "", []


async def transcribe_chunk_with_timestamps(
    audio_chunk: str,
    chunk_offset: float = 0.0,
) -> Tuple[str, List[WordTiming]]:
    """
    Transcribe a chunk with word timestamps, adjusting times by chunk offset.

    Args:
        audio_chunk: Path to the audio chunk file
        chunk_offset: Time offset in seconds to add to all word timestamps

    Returns:
        Tuple of (transcribed text, list of word timings with adjusted times)
    """
    try:
        logger.debug(f"Transcribing chunk with timestamps: {audio_chunk}, offset: {chunk_offset}s")

        async with _TRANSCRIBE_SEM:
            text, word_timings = await _transcribe_with_word_timestamps_impl(
                audio_chunk, settings.WHISPER_MODEL
            )

        # Adjust timestamps by chunk offset
        if chunk_offset > 0:
            adjusted_timings = [
                WordTiming(
                    word=wt.word,
                    start_time=wt.start_time + chunk_offset,
                    end_time=wt.end_time + chunk_offset,
                    confidence=wt.confidence,
                )
                for wt in word_timings
            ]
            return text, adjusted_timings

        return text, word_timings

    except Exception as e:
        logger.error(f"Error transcribing chunk with timestamps: {e}")
        return "", []


__all__ = [
    "transcribe_audio",
    "transcribe_audio_chunk",
    "transcribe_audio_local",
    "transcribe_chunk_with_timestamps",
]
