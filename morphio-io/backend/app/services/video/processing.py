import asyncio
import json
import logging
import os
from typing import Optional, Union, Dict, Any
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

from ...config import settings
from ...schemas.audio_schema import (
    AudioProcessingInput,
    TranscriptionResult,
    TranscriptionStatus,
)
from ...schemas.media_schema import (
    MediaProcessingInput,
    MediaProcessingStatusResponse,
    MediaSource,
    MediaType,
)
from ...utils.cache_utils import (
    cache_generated_content,
    cache_transcription,
    cache_whisper_transcription,
    compute_template_hash,
    get_cached_generated_content,
    get_cached_transcription,
    get_cached_whisper_transcription,
)
from ...utils.enums import JobStatus as JS
from ...utils.enums import TranscriptionSource, UsageType
from ...utils.error_handlers import ApplicationException
from ...utils.file_utils import compute_file_hash, compute_hash, delete_file
from ...utils.job_utils import enqueue_task
from ...utils.transcription_utils import clean_transcription
from ...adapters.video import (
    download_video_via_ytdlp,
    get_yt_video_id,
    is_supported_video_url,
)
from ..audio import chunk_audio_file, transcribe_audio, transcribe_audio_chunk
from ..generation import generate_content_from_transcript, save_generated_content
from ..job import get_job_status, update_job_status
from ..template import load_template
from ..usage import increment_usage
from .yt_types import TranscriptList, TranscriptEntry

logger = logging.getLogger(__name__)


@retry(stop=stop_after_attempt(1), wait=wait_exponential(multiplier=1, min=2, max=10))
async def process_online_video(
    url: str,
    output_directory: Optional[str] = None,
    job_id: Optional[str] = None,
    is_youtube=True,
) -> TranscriptionResult:
    try:
        if not url or not output_directory or not job_id:
            raise ApplicationException(
                "Missing parameters for process_online_video", status_code=400
            )
        if not is_supported_video_url(url):
            raise ApplicationException("Unsupported video URL", status_code=400)

        video_id = None
        if is_youtube:
            video_id = get_yt_video_id(url)

        if is_youtube and video_id is not None:
            cached_result = await get_cached_transcription(video_id, TranscriptionSource.YOUTUBE)
            if cached_result:
                return cached_result

            # Try to fetch YouTube transcript if library available; otherwise skip
            try:
                from youtube_transcript_api import (  # type: ignore[reportMissingImports]
                    NoTranscriptFound,
                    YouTubeTranscriptApi,
                )

                # Prefer class method list_transcripts if available; else fall back to get_transcript
                from typing import cast

                entries: list[TranscriptEntry]
                if hasattr(YouTubeTranscriptApi, "list_transcripts"):
                    transcript_list_any = YouTubeTranscriptApi.list_transcripts(video_id)  # type: ignore[attr-defined]
                    transcript_list = cast(TranscriptList, transcript_list_any)
                    try:
                        transcript = transcript_list.find_manually_created_transcript(
                            ["en", "en-US"]
                        )
                        logger.debug(f"Found manually-created transcript for {video_id}")
                    except NoTranscriptFound:
                        logger.debug(f"No manual transcript, checking auto for {video_id}")
                        transcript = transcript_list.find_generated_transcript(["en", "en-US"])
                    entries = transcript.fetch()
                else:
                    logger.debug(
                        "list_transcripts not on YouTubeTranscriptApi; using get_transcript"
                    )
                    get_tx = getattr(YouTubeTranscriptApi, "get_transcript")
                    entries = cast(
                        list[TranscriptEntry],
                        get_tx(video_id, languages=["en", "en-US"]),  # type: ignore[misc]
                    )

                full_text = " ".join(e.get("text", "") for e in entries)
                if full_text.strip():
                    result = TranscriptionResult(
                        text=clean_transcription(full_text),
                        confidence=None,
                        status=TranscriptionStatus.COMPLETED,
                        source=TranscriptionSource.YOUTUBE,
                        metadata={"transcript_entries": entries},
                        error=None,
                    )
                    await cache_transcription(video_id, result, TranscriptionSource.YOUTUBE)
                    return result
            except Exception as e:
                logger.info(f"YouTube transcript library unavailable or failed: {e}")

        # fallback
        logger.info("Attempting fallback local approach via ffmpeg + whisper.")
        await update_job_status(job_id, JS.PROCESSING.value, 30, "Downloading audio")
        raw_path = await download_video_via_ytdlp(
            url, output_directory, job_id=job_id, video_id=video_id
        )
        await update_job_status(job_id, JS.PROCESSING.value, 40, "Converting to mp3")
        result_text = await process_local_video(raw_path, output_directory, job_id)
        if result_text and result_text.strip():
            final_result = TranscriptionResult(
                text=clean_transcription(result_text),
                confidence=None,
                status=TranscriptionStatus.COMPLETED,
                source=TranscriptionSource.WHISPER,
                error=None,
            )
            if is_youtube and video_id:
                await cache_transcription(video_id, final_result, TranscriptionSource.WHISPER)
            return final_result
        else:
            raise ApplicationException("Downloaded/transcribed video returned empty result")

    except ApplicationException as ae:
        raise ae
    except Exception as e:
        logger.error(f"Error in process_online_video: {e}", exc_info=True)
        return TranscriptionResult(
            text="",
            confidence=None,
            status=TranscriptionStatus.FAILED,
            source=TranscriptionSource.WHISPER,
            error=str(e),
        )


async def process_local_video(video_path: str, upload_dir: str, job_id: str) -> str:
    audio_path = video_path
    chunk_paths: list[str] = []
    try:
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        if settings.AUDIO_TRANSCRIPTION_MODEL.lower() == "local":
            transcription = await transcribe_audio(audio_path)
            if not transcription or transcription.status != TranscriptionStatus.COMPLETED:
                err = transcription.error if transcription else "Unknown error"
                raise ApplicationException(f"Transcription failed: {err}")
            if not transcription.text:
                raise ApplicationException("Transcription returned empty result")
            return transcription.text
        else:
            audio_input = AudioProcessingInput(
                file_path=audio_path,
                output_directory=upload_dir,
                max_file_size_MB=25,
                overlap_ms=2000,
            )
            chunk_result = await chunk_audio_file(audio_input)
            chunk_paths = [c.chunk_path for c in chunk_result.chunks]

            transcriptions = await asyncio.gather(
                *[transcribe_audio_chunk(cp) for cp in chunk_paths]
            )
            non_empty = [t for t in transcriptions if t.strip()]
            if not non_empty:
                raise ApplicationException("No valid transcriptions generated")

            return " ".join(non_empty)

    except ApplicationException as ae:
        logger.error(f"process_local_video error: {ae.message}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise ApplicationException(f"Video processing failed: {str(e)}")
    finally:
        for cp in chunk_paths:
            if os.path.exists(cp):
                await delete_file(cp)


async def validate_video_input(input_path: str) -> bool:
    if not input_path:
        return False
    try:
        parsed = urlparse(input_path)
        if all([parsed.scheme, parsed.netloc]):
            return True
    except ValueError:
        pass

    ext = os.path.splitext(input_path)[1].lower().lstrip(".")
    video_exts = [
        "mp4",
        "m4v",
        "mov",
        "avi",
        "wmv",
        "flv",
        "mkv",
        "webm",
        "mpeg",
        "mpg",
        "3gp",
        "ogg",
        "m4a",
        "mp3",
    ]
    return ext in video_exts


@retry(stop=stop_after_attempt(1), wait=wait_exponential(min=2, max=10))
async def transcribe_and_generate_video(
    input_data: Union[MediaProcessingInput, Dict[str, Any]],
    job_id: str,
    db: AsyncSession,
    user_id: int,
) -> None:
    try:
        # Coerce from dict when coming from the generic job queue
        if isinstance(input_data, dict):
            input_data = MediaProcessingInput.model_validate(input_data)
        if input_data.media_type != MediaType.VIDEO:
            raise ApplicationException("Invalid media type for video processing", 400)

        # Get model_name from JobStatusInfo via job_id
        job_status = await get_job_status(job_id)
        chosen_model = getattr(job_status, "chosen_model", None) or settings.CONTENT_MODEL

        logger.debug(f"Using model: {chosen_model} for job {job_id}")

        await update_job_status(job_id, JS.PROCESSING.value, 0, "Starting video processing")

        input_path = str(input_data.url or input_data.file_path)
        if not await validate_video_input(input_path):
            raise ApplicationException("Invalid video input", 400)

        await update_job_status(job_id, JS.PROCESSING.value, 20, "Input validated, template loaded")

        skip_generation = input_data.template_id == 0
        template_content = ""
        template_hash = ""
        if not skip_generation:
            template_content = await load_template(input_data.template_id, db)
            template_hash = compute_template_hash(template_content)

        if input_data.source == MediaSource.YOUTUBE:
            await increment_usage(db, user_id, UsageType.VIDEO_PROCESSING)
            transcription = await process_online_video(
                input_path, settings.UPLOAD_DIR, job_id, True
            )
        elif input_data.source in [MediaSource.RUMBLE, MediaSource.TWITTER, MediaSource.TIKTOK]:
            await increment_usage(db, user_id, UsageType.VIDEO_PROCESSING)
            # For Twitter and TikTok, we won't try YouTube transcript API (False)
            transcription = await process_online_video(
                input_path, settings.UPLOAD_DIR, job_id, False
            )
        else:
            await increment_usage(db, user_id, UsageType.VIDEO_PROCESSING)
            if not input_data.file_path:
                raise ApplicationException("No local video file provided", 400)
            file_hash = await compute_file_hash(input_data.file_path)
            cached_whisper = await get_cached_whisper_transcription(file_hash)
            if cached_whisper:
                transcription = json.loads(cached_whisper)
            else:
                raw_text = await process_local_video(
                    input_data.file_path, settings.UPLOAD_DIR, job_id
                )
                await cache_whisper_transcription(file_hash, raw_text)
                transcription = raw_text

        await update_job_status(
            job_id, JS.PROCESSING.value, 70, "Transcription complete, preparing result"
        )

        if isinstance(transcription, str):
            transcription_text = transcription
        elif isinstance(transcription, dict) and "text" in transcription:
            transcription_text = transcription["text"]
        elif isinstance(transcription, TranscriptionResult):
            transcription_text = transcription.text
        else:
            raise ApplicationException("Unexpected transcription format", 500)

        if not transcription_text:
            raise ApplicationException("Transcription failed or empty result", 500)

        if skip_generation:
            result_data = {
                "content": transcription_text,
                "title": "Transcript Only",
                "content_id": None,
                "user_id": user_id,
                "template_id": 0,
            }
            await update_job_status(
                job_id,
                JS.COMPLETED.value,
                100,
                "Transcript-only processing complete",
                result_data,
            )
            return

        transcript_hash = compute_hash(transcription_text)
        cached_content = await get_cached_generated_content(
            transcript_hash,
            str(input_data.template_id),
            template_hash,
            user_id,
            chosen_model,
        )
        if cached_content:
            generated_content = json.loads(cached_content)
        else:
            generated_content = await generate_content_from_transcript(
                transcription_text, template_content, chosen_model=chosen_model
            )
            await cache_generated_content(
                transcript_hash,
                str(input_data.template_id),
                template_hash,
                user_id,
                generated_content,
                chosen_model,
            )

        await increment_usage(db, user_id, UsageType.CONTENT_GENERATION)

        if input_data.source in [
            MediaSource.YOUTUBE,
            MediaSource.RUMBLE,
            MediaSource.TWITTER,
            MediaSource.TIKTOK,
        ]:
            generated_content += f"\n\nSource: [{input_data.url}]({input_data.url})"

        try:
            saved = await save_generated_content(generated_content, user_id)
            logger.info(f"Content saved for user {user_id}")
            ret_data = {
                "content": saved.content,
                "title": saved.title,
                "content_id": saved.id,
                "user_id": user_id,
                "template_id": input_data.template_id,
            }
            await update_job_status(
                job_id, JS.COMPLETED.value, 100, "Processing complete", ret_data
            )
        except ApplicationException as ae:
            logger.error(f"Failed to save content: {ae.message}")
            ret_data = {"content": generated_content}
            await update_job_status(
                job_id,
                JS.FAILED.value,
                100,
                "Processing complete (content not saved)",
                ret_data,
            )

    except ApplicationException as ae:
        logger.error(f"Application error: {ae.message}", exc_info=True)
        await update_job_status(job_id, JS.FAILED.value, 100, f"Error: {ae.message}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        await update_job_status(
            job_id, JS.FAILED.value, 100, f"Unexpected error: {str(e)}", error=str(e)
        )


async def enqueue_video_processing(
    input_data: MediaProcessingInput, db: AsyncSession, model_name: str = ""
) -> str:
    return await enqueue_task(
        transcribe_and_generate_video, input_data.model_dump(), db, input_data.user_id, model_name
    )


async def get_video_processing_status(job_id: str, user_id: int) -> MediaProcessingStatusResponse:
    st = await get_job_status(job_id)
    if st.user_id != user_id:
        raise ApplicationException("Not authorized to access this job", 403)
    return MediaProcessingStatusResponse(
        job_id=job_id,
        status=st.status,
        progress=st.progress,
        stage=st.stage,
        message=st.message,
        result=st.result if isinstance(st.result, (str, dict)) else None,
        error=st.error,
    )
