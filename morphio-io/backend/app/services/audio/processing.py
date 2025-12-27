"""Audio transcription and content generation orchestration.

This module coordinates the audio processing workflow:
1. Download/acquire audio (YouTube or uploaded file)
2. Chunk into segments for transcription
3. Transcribe with optional speaker diarization
4. Generate content from transcript
5. Save and cache results
"""

import json
import logging
from typing import Any, Dict, List, Union

from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...schemas.audio_schema import AudioProcessingInput
from ...schemas.diarization_schema import TranscriptionSpeakerSegment
from ...schemas.media_schema import MediaProcessingInput, MediaProcessingStatusResponse
from ...utils.cache_utils import (
    cache_generated_content,
    cache_whisper_transcription,
    compute_template_hash,
    get_cached_generated_content,
    get_cached_whisper_transcription,
)
from ...utils.enums import JobStatus, ProcessingStage, UsageType
from ...utils.error_handlers import ApplicationException
from ...utils.file_utils import compute_file_hash, compute_hash
from ...utils.job_utils import enqueue_task
from ...adapters.video import download_video_via_ytdlp
from ..generation import generate_content_from_transcript, save_generated_content
from ..job import get_job_status, update_job_status
from ..template import load_template
from ..usage import increment_usage
from .chunking import chunk_audio_file, cleanup_chunks
from .pipeline import (
    should_use_diarization,
    transcribe_chunks_standard,
    transcribe_with_diarization,
)

logger = logging.getLogger(__name__)

# Re-export for backward compatibility
__all__ = [
    "transcribe_and_generate_audio",
    "enqueue_audio_processing",
    "get_audio_processing_status",
    "chunk_audio_file",
    "cleanup_chunks",
    "transcribe_with_diarization",
]


async def transcribe_and_generate_audio(
    input_data: Union[MediaProcessingInput, Dict[str, Any]],
    job_id: str,
    db: AsyncSession,
    user_id: int,
) -> None:
    """Handle audio transcription and content generation."""
    try:
        if isinstance(input_data, dict):
            input_data = MediaProcessingInput.model_validate(input_data)

        job_status = await get_job_status(job_id)
        chosen_model = getattr(job_status, "chosen_model", None) or settings.CONTENT_MODEL
        logger.debug(f"Using model: {chosen_model} for job {job_id}")

        await update_job_status(
            job_id,
            JobStatus.PROCESSING.value,
            0,
            "Starting audio processing",
            stage=ProcessingStage.QUEUED,
        )

        input_path = str(input_data.url or input_data.file_path)
        if not input_path:
            raise ApplicationException("No audio input provided", status_code=400)

        await update_job_status(
            job_id,
            JobStatus.PROCESSING.value,
            20,
            "Input validated, template loaded",
            stage=ProcessingStage.DOWNLOADING,
        )

        skip_generation = input_data.template_id == 0
        template_content = ""
        template_hash = ""
        if not skip_generation:
            template_content = await load_template(input_data.template_id, db)
            template_hash = compute_template_hash(template_content)

        # Acquire audio file
        if input_data.source.value == "youtube":
            await increment_usage(db, input_data.user_id, UsageType.AUDIO_PROCESSING)
            await update_job_status(
                job_id,
                JobStatus.PROCESSING.value,
                30,
                "Downloading audio",
                stage=ProcessingStage.DOWNLOADING,
            )
            audio_file = await download_video_via_ytdlp(
                input_path, settings.UPLOAD_DIR, job_id=job_id
            )
        else:
            audio_file = input_data.file_path
            await increment_usage(db, input_data.user_id, UsageType.AUDIO_PROCESSING)

        if not audio_file:
            raise ApplicationException("No audio file provided", status_code=400)

        file_hash = await compute_file_hash(audio_file)
        cached_transcription = await get_cached_whisper_transcription(file_hash)

        enable_diarization = getattr(input_data, "enable_diarization", False)
        min_speakers = getattr(input_data, "min_speakers", None)
        max_speakers = getattr(input_data, "max_speakers", None)

        speaker_segments: List[TranscriptionSpeakerSegment] = []
        num_speakers = 0
        cache_suffix = "_diarized" if enable_diarization else ""

        if cached_transcription:
            transcription_text = _load_cached_transcription(
                cached_transcription, enable_diarization
            )
            if isinstance(transcription_text, tuple):
                transcription_text, speaker_segments, num_speakers = transcription_text
        else:
            transcription_text, speaker_segments, num_speakers = await _transcribe_audio(
                audio_file,
                job_id,
                enable_diarization,
                min_speakers,
                max_speakers,
                file_hash,
                cache_suffix,
            )

        await update_job_status(
            job_id,
            JobStatus.PROCESSING.value,
            70,
            "Transcription complete, preparing result",
            stage=ProcessingStage.GENERATING,
        )

        if not transcription_text.strip():
            raise ApplicationException(
                "Failed to transcribe audio or empty result", status_code=500
            )

        if skip_generation:
            result = _build_transcript_only_result(
                transcription_text, input_data.user_id, speaker_segments, num_speakers
            )
            await update_job_status(
                job_id,
                JobStatus.COMPLETED.value,
                100,
                "Transcript-only processing complete",
                result=result,
                stage=ProcessingStage.COMPLETED,
            )
            return

        # Generate content
        generated_content = await _generate_or_get_cached_content(
            transcription_text,
            template_content,
            template_hash,
            input_data.template_id,
            input_data.user_id,
            chosen_model,
        )
        await increment_usage(db, input_data.user_id, UsageType.CONTENT_GENERATION)

        if input_data.source.value == "youtube":
            generated_content += f"\n\nSource: [{input_data.url}]({input_data.url})"

        await _save_and_complete(generated_content, input_data, job_id)

    except ApplicationException as ae:
        logger.error(f"Application error: {ae.message}", exc_info=True)
        await update_job_status(
            job_id,
            JobStatus.FAILED.value,
            100,
            f"Error: {ae.message}",
            stage=ProcessingStage.FAILED,
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        await update_job_status(
            job_id,
            JobStatus.FAILED.value,
            100,
            f"Unexpected error: {str(e)}",
            error=str(e),
            stage=ProcessingStage.FAILED,
        )


def _load_cached_transcription(cached: str, enable_diarization: bool):
    """Load transcription from cache, returning speaker data if available."""
    try:
        data = json.loads(cached)
        if isinstance(data, dict):
            text = data.get("text", "")
            if enable_diarization and "speakers" in data:
                segments = [TranscriptionSpeakerSegment(**s) for s in data.get("speakers", [])]
                return text, segments, data.get("num_speakers", 0)
            return text
        return cached
    except json.JSONDecodeError:
        return cached


async def _transcribe_audio(
    audio_file: str,
    job_id: str,
    enable_diarization: bool,
    min_speakers: int | None,
    max_speakers: int | None,
    file_hash: str,
    cache_suffix: str,
) -> tuple[str, List[TranscriptionSpeakerSegment], int]:
    """Chunk and transcribe audio, with optional diarization."""
    await update_job_status(
        job_id,
        JobStatus.PROCESSING.value,
        40,
        "Chunking audio",
        stage=ProcessingStage.CHUNKING,
    )

    audio_input = AudioProcessingInput(
        file_path=audio_file,
        output_directory=settings.UPLOAD_DIR,
        max_file_size_MB=25,
        overlap_ms=2000,
    )
    chunk_result = await chunk_audio_file(audio_input)
    chunk_paths = [c.chunk_path for c in chunk_result.chunks]

    try:
        if should_use_diarization(enable_diarization):
            logger.info("Diarization enabled, using diarization pipeline")
            text, segments, num = await transcribe_with_diarization(
                audio_file, chunk_result.chunks, job_id, min_speakers, max_speakers
            )
            if text:
                cache_data = {
                    "text": text,
                    "speakers": [s.model_dump() for s in segments],
                    "num_speakers": num,
                    "diarization_enabled": True,
                }
                await cache_whisper_transcription(file_hash + cache_suffix, json.dumps(cache_data))
            return text, segments, num
        else:
            text = await transcribe_chunks_standard(chunk_paths, job_id)
            if text:
                await cache_whisper_transcription(file_hash, json.dumps({"text": text}))
            return text, [], 0
    finally:
        await cleanup_chunks(chunk_paths)


def _build_transcript_only_result(
    text: str, user_id: int, segments: List[TranscriptionSpeakerSegment], num_speakers: int
) -> dict:
    """Build result dict for transcript-only mode."""
    result = {
        "content": text,
        "title": "Transcript Only",
        "content_id": None,
        "user_id": user_id,
        "template_id": 0,
    }
    if segments:
        result["speakers"] = [s.model_dump() for s in segments]
        result["num_speakers"] = num_speakers
        result["diarization_enabled"] = True
    return result


async def _generate_or_get_cached_content(
    transcription: str,
    template: str,
    template_hash: str,
    template_id: int,
    user_id: int,
    model: str,
) -> str:
    """Generate content or retrieve from cache."""
    transcript_hash = compute_hash(transcription)
    cached = await get_cached_generated_content(
        transcript_hash, str(template_id), template_hash, user_id, model
    )

    if cached:
        return json.loads(cached)

    content = await generate_content_from_transcript(transcription, template, model)
    await cache_generated_content(
        transcript_hash, str(template_id), template_hash, user_id, content, model
    )
    return content


async def _save_and_complete(content: str, input_data: MediaProcessingInput, job_id: str) -> None:
    """Save generated content and update job status."""
    try:
        saved = await save_generated_content(content, input_data.user_id)
        logger.info(f"Content saved for user {input_data.user_id}")
        result = {
            "content": saved.content,
            "title": saved.title,
            "content_id": saved.id,
            "user_id": input_data.user_id,
            "template_id": input_data.template_id,
        }
        await update_job_status(
            job_id,
            JobStatus.COMPLETED.value,
            100,
            "Processing complete",
            result=result,
            stage=ProcessingStage.COMPLETED,
        )
    except ApplicationException as ae:
        logger.error(f"Failed to save content: {ae.message}")
        await update_job_status(
            job_id,
            JobStatus.FAILED.value,
            100,
            "Processing complete (content not saved)",
            result={"content": content},
            stage=ProcessingStage.FAILED,
        )


async def enqueue_audio_processing(
    input_data: MediaProcessingInput, db: AsyncSession, model_name: str = ""
) -> str:
    """Enqueue audio processing task."""
    return await enqueue_task(
        transcribe_and_generate_audio,
        input_data.model_dump(),
        db,
        input_data.user_id,
        model_name,
    )


async def get_audio_processing_status(job_id: str, user_id: int):
    """Get status of audio processing job."""
    status = await get_job_status(job_id)
    if status.user_id != user_id:
        raise ApplicationException("Not authorized to access this job", status_code=403)
    return MediaProcessingStatusResponse(
        job_id=job_id,
        status=status.status,
        progress=status.progress,
        stage=status.stage,
        message=status.message,
        result=status.result if isinstance(status.result, (str, dict)) else None,
        error=status.error,
    )
