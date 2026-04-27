"""Purpose: Preserve the legacy video-processing facade used by cache-focused callers and tests.
Responsibilities: Coordinate transcript caching, content generation, and persistence for video inputs.
Scope: Compatibility orchestration layer only; new runtime video processing lives under app.services.video.
Usage: Imported by tests and the app.services.video package as process_video.
Invariants/Assumptions: YouTube transcript helpers return plain transcript text and must cache by video ID.
"""

from __future__ import annotations

import json
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..schemas.media_schema import MediaProcessingInput, MediaSource
from ..utils.cache_utils import (
    cache_generated_content,
    cache_whisper_transcription,
    cache_youtube_transcript,
    compute_template_hash,
    get_cached_generated_content,
    get_cached_whisper_transcription,
    get_cached_youtube_transcript,
)
from ..utils.enums import ProcessingStage
from ..utils.error_handlers import ApplicationException
from ..utils.file_utils import compute_file_hash, compute_hash
from ..adapters.video import get_yt_video_id
from .generation.core import generate_content_from_transcript
from .generation.storage import save_generated_content
from .job.status import update_job_status
from .video.processing import process_local_video, process_online_video


async def process_youtube_video(url: str, output_directory: Optional[str] = None) -> str:
    """Return transcript text for a YouTube URL through the canonical online processor."""
    result = await process_online_video(
        url,
        output_directory or settings.UPLOAD_DIR,
        job_id="legacy-youtube-wrapper",
        is_youtube=True,
    )
    if result.error or not result.text:
        raise ApplicationException(
            result.error or "YouTube transcript processing returned empty text", 500
        )
    return result.text


async def load_template(template_id: int, db: AsyncSession) -> str:
    from .template import load_template as _lt

    tpl = await _lt(template_id, db)
    if isinstance(tpl, dict):
        return json.dumps(tpl)
    return str(tpl)


async def process_video(input_data: MediaProcessingInput, job_id: str, db: AsyncSession) -> dict:
    """Orchestrate video processing with caching hooks expected by tests."""
    if input_data.template_id is None:
        raise ApplicationException("Template ID is required", 400)

    # Load template and compute template hash for content caching
    template_content = await load_template(int(input_data.template_id), db)
    template_hash = compute_template_hash(template_content)

    # Obtain transcript (YouTube or local upload) with caching
    transcript_text: Optional[str] = None
    if input_data.source == MediaSource.YOUTUBE and input_data.url:
        video_id = get_yt_video_id(str(input_data.url))
        if video_id is None:
            raise ApplicationException("Invalid YouTube URL", 400)
        cached = await get_cached_youtube_transcript(video_id)
        if cached:
            cached_value = json.loads(cached)
            transcript_text = (
                cached_value.get("text", "") if isinstance(cached_value, dict) else cached_value
            )
        else:
            # Delegate to function expected by tests (patched in the test)
            transcript_text = await process_youtube_video(str(input_data.url))
            await cache_youtube_transcript(video_id, transcript_text)
    else:
        # Local file path; cache by file hash
        if not input_data.file_path:
            raise ApplicationException("File path required for upload source", 400)
        fh = await compute_file_hash(input_data.file_path)
        cached = await get_cached_whisper_transcription(fh)
        if cached:
            cached_value = json.loads(cached)
            transcript_text = (
                cached_value.get("text", "") if isinstance(cached_value, dict) else cached_value
            )
        else:
            # Delegate to underlying local processing function (patcheable in tests)
            transcript_text = await process_local_video(
                input_data.file_path, settings.UPLOAD_DIR, job_id
            )
            await cache_whisper_transcription(fh, transcript_text)

    if not transcript_text:
        raise ApplicationException("Empty transcript", 500)

    # Check generated content cache
    transcript_hash = compute_hash(transcript_text)
    model_name = (
        getattr(input_data, "model_name", None) or "gpt-4"
    )  # Default to gpt-4 if not specified or None
    cached_content = await get_cached_generated_content(
        transcript_hash,
        str(int(input_data.template_id)),
        template_hash,
        int(input_data.user_id),
        model_name,
    )
    if cached_content:
        content = json.loads(cached_content)
    else:
        content = await generate_content_from_transcript(transcript_text, template_content)
        await cache_generated_content(
            transcript_hash,
            str(int(input_data.template_id)),
            template_hash,
            int(input_data.user_id),
            content,
            model_name,
        )

    # Save content (patched in tests if needed)
    await save_generated_content(content, int(input_data.user_id), int(input_data.template_id))
    await update_job_status(
        job_id,
        "completed",
        100,
        "Done",
        stage=ProcessingStage.COMPLETED,
    )

    return {"status": "success", "content": content}
