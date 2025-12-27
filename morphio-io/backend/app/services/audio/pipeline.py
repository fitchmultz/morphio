"""Transcription pipeline with optional speaker diarization."""

import asyncio
import logging
from typing import List, Optional, Tuple

from ...schemas.audio_schema import AudioChunk
from ...schemas.diarization_schema import TranscriptionSpeakerSegment, WordTiming
from ...utils.enums import JobStatus, ProcessingStage
from ..job import update_job_status
from .diarization import is_diarization_available, run_diarization
from .speaker_alignment import (
    align_speakers_to_words,
    format_diarized_transcript,
    utterances_to_segments,
)
from .transcription import transcribe_audio_chunk, transcribe_chunk_with_timestamps

logger = logging.getLogger(__name__)


async def transcribe_with_diarization(
    audio_file: str,
    chunks: List[AudioChunk],
    job_id: str,
    min_speakers: Optional[int] = None,
    max_speakers: Optional[int] = None,
) -> Tuple[str, List[TranscriptionSpeakerSegment], int]:
    """
    Transcribe audio with speaker diarization.

    Runs diarization in parallel with transcription for efficiency,
    then aligns speaker segments with word timings.

    Args:
        audio_file: Path to the original audio file
        chunks: List of audio chunks with timing info
        job_id: Job ID for progress updates
        min_speakers: Minimum expected speakers (optional)
        max_speakers: Maximum expected speakers (optional)

    Returns:
        Tuple of (formatted diarized text, speaker segments, num_speakers)
    """
    chunk_paths = [c.chunk_path for c in chunks]
    chunk_offsets = [c.start_time for c in chunks]

    # Start diarization on full audio in background
    await update_job_status(
        job_id,
        JobStatus.PROCESSING.value,
        45,
        "Starting speaker diarization",
        stage=ProcessingStage.DIARIZING,
    )
    diarization_task = asyncio.create_task(run_diarization(audio_file, min_speakers, max_speakers))

    # Transcribe chunks with word timestamps
    all_word_timings: List[WordTiming] = []
    transcriptions: List[str] = []
    total = len(chunk_paths)

    for idx, (cp, offset) in enumerate(zip(chunk_paths, chunk_offsets), start=1):
        await update_job_status(
            job_id,
            JobStatus.PROCESSING.value,
            50 + int(10 * idx / max(total, 1)),
            f"Transcribing chunk {idx}/{total} with timestamps",
            stage=ProcessingStage.TRANSCRIBING,
        )
        text, word_timings = await transcribe_chunk_with_timestamps(cp, offset)
        transcriptions.append(text)
        all_word_timings.extend(word_timings)

    # Wait for diarization to complete
    await update_job_status(
        job_id,
        JobStatus.PROCESSING.value,
        62,
        "Waiting for diarization",
        stage=ProcessingStage.DIARIZING,
    )

    try:
        diarization_result = await diarization_task
    except Exception as e:
        logger.error(f"Diarization failed, returning plain transcription: {e}")
        # Graceful degradation - return plain transcription
        plain_text = " ".join(filter(None, transcriptions))
        return plain_text, [], 0

    # Align speakers to words
    await update_job_status(
        job_id,
        JobStatus.PROCESSING.value,
        65,
        "Aligning speakers to transcript",
        stage=ProcessingStage.DIARIZING,
    )

    utterances = align_speakers_to_words(diarization_result, all_word_timings)
    speaker_segments = utterances_to_segments(utterances)

    # Format diarized transcript with inline labels
    diarized_text = format_diarized_transcript(speaker_segments)

    logger.info(
        f"Diarization complete: {diarization_result.num_speakers} speakers, "
        f"{len(speaker_segments)} segments"
    )

    return diarized_text, speaker_segments, diarization_result.num_speakers


async def transcribe_chunks_standard(
    chunk_paths: List[str],
    job_id: str,
) -> str:
    """
    Standard transcription without diarization.

    Args:
        chunk_paths: List of audio chunk file paths
        job_id: Job ID for progress updates

    Returns:
        Concatenated transcription text
    """
    transcriptions: List[str] = []
    total = len(chunk_paths)

    for idx, cp in enumerate(chunk_paths, start=1):
        await update_job_status(
            job_id,
            JobStatus.PROCESSING.value,
            50 + int(15 * idx / max(total, 1)),
            f"Transcribing chunk {idx}/{total}",
            stage=ProcessingStage.TRANSCRIBING,
        )
        transcriptions.append(await transcribe_audio_chunk(cp))

    return " ".join(filter(None, transcriptions))


def should_use_diarization(enable_diarization: bool) -> bool:
    """Check if diarization should be used."""
    if not enable_diarization:
        return False

    if not is_diarization_available():
        logger.warning(
            "Diarization requested but not available "
            "(check DIARIZATION_ENABLED and HUGGING_FACE_TOKEN)"
        )
        return False

    return True
