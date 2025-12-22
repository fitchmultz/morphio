import asyncio
import logging
from pathlib import Path
from typing import Annotated, Optional


import aiofiles
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..models.user import User
from ..schemas.media_schema import (
    MediaProcessingInput,
    MediaProcessingResponse,
    MediaProcessingStatusResponse,
    MediaSource,
    MediaType,
)
from ..schemas.response_schema import ResponseModel
from ..services.audio import enqueue_audio_processing, get_audio_processing_status
from ..services.generation.core import MODEL_DISPLAY_INFO, VALID_GENERATION_MODELS
from ..services.security import get_current_user
from ..services.template import get_template_by_name
from ..services.video import enqueue_video_processing, get_video_processing_status
from ..utils.cache_utils import get_cache
from ..utils.decorators import rate_limit, require_auth
from ..utils.enums import JobStatus, ResponseStatus, MediaProcessingStatus
from ..utils.error_handlers import ApplicationException
from ..utils.file_utils import get_unique_filename, is_allowed_file, sanitize_filename
from ..utils.response_utils import create_response
from ..utils.route_helpers import common_responses, handle_route_errors
from ..utils.youtube_utils import is_supported_video_url

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/config",
    operation_id="get_media_config",
    response_model=ResponseModel[dict],
    responses={
        200: {
            "description": "Media file configuration",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Media file configuration",
                        "data": {
                            "video_extensions": ["mp4", "webm", "mov", "avi"],
                            "audio_extensions": ["mp3", "wav", "aac", "flac"],
                            "max_upload_size": 3221225472,
                        },
                    }
                }
            },
        },
        **common_responses,
    },
)
@rate_limit("200/minute")
@handle_route_errors
async def get_media_file_configuration():
    """Get media file configuration including allowed extensions."""
    logger.info("Retrieving media file configuration")

    config = {
        "video_extensions": settings.ALLOWED_VIDEO_EXTENSIONS,
        "audio_extensions": settings.ALLOWED_AUDIO_EXTENSIONS,
        "max_upload_size": settings.MAX_UPLOAD_SIZE,
    }

    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Media file configuration",
        data=config,
        status_code=status.HTTP_200_OK,
    )


@router.get(
    "/models",
    operation_id="get_available_models",
    response_model=ResponseModel[list],
    responses={
        200: {
            "description": "Available AI models for content generation",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Available models",
                        "data": [
                            {"id": "gemini-3-flash-preview", "label": "Gemini 3 Flash (High)"},
                            {"id": "gpt-5.1", "label": "GPT-5.1"},
                        ],
                    }
                }
            },
        },
        **common_responses,
    },
)
@rate_limit("200/minute")
@handle_route_errors
async def get_available_models():
    """Get available AI models for content generation."""
    logger.info("Retrieving available models")

    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Available models",
        data=MODEL_DISPLAY_INFO,
        status_code=status.HTTP_200_OK,
    )


@router.post(
    "/process-media",
    operation_id="process_media",
    response_model=MediaProcessingResponse,
    responses={
        200: {"description": "Media processing job enqueued successfully"},
        400: {"description": "Bad Request"},
        413: {"description": "Payload Too Large"},
        404: {"description": "Template not found"},
        **common_responses,
    },
)
@rate_limit("100/minute")
@require_auth
@handle_route_errors
async def process_media_route(
    input_url: str = Form(None),
    template_id: str = Form(...),
    input_file: Optional[UploadFile] = File(None),
    model: str = Form(None),
    media_type: str = Form(...),
    enable_diarization: bool = Form(False),
    min_speakers: Optional[int] = Form(None),
    max_speakers: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    media_type_enum = MediaType(media_type.lower())

    # Validate diarization parameters
    if enable_diarization:
        if min_speakers is not None:
            if min_speakers < 1 or min_speakers > 20:
                raise ApplicationException(
                    message="min_speakers must be between 1 and 20",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
        if max_speakers is not None:
            if max_speakers < 1 or max_speakers > 20:
                raise ApplicationException(
                    message="max_speakers must be between 1 and 20",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
        if min_speakers is not None and max_speakers is not None:
            if min_speakers > max_speakers:
                raise ApplicationException(
                    message="min_speakers cannot be greater than max_speakers",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

    if template_id.isdigit():
        template_id_int: int = int(template_id)
    else:
        fetched_id = await get_template_by_name(db, template_id)
        if fetched_id is None:
            raise ApplicationException(
                message="Template not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        template_id_int = int(fetched_id)

    if input_url:
        if not is_supported_video_url(input_url):
            if "spotify.com" in input_url:
                raise ApplicationException(
                    message="Spotify processing is not yet supported",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            raise ApplicationException(
                message="Invalid URL. Only YouTube, Rumble, X.com (Twitter), and TikTok URLs are supported.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    if not input_url and not input_file:
        raise ApplicationException(
            message="Either video URL or media file is required",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    model_name = model if model and model in VALID_GENERATION_MODELS else ""

    media_input = MediaProcessingInput(
        source=MediaSource.YOUTUBE if input_url else MediaSource.UPLOAD,
        # Pydantic coerces str to AnyHttpUrl at runtime
        url=input_url if input_url else None,  # ty: ignore[invalid-argument-type]
        file_path=None,
        template_id=template_id_int,
        user_id=int(current_user.id),
        media_type=media_type_enum,
        model_name=model_name,
        enable_diarization=enable_diarization,
        min_speakers=min_speakers,
        max_speakers=max_speakers,
    )

    # Detect the correct source based on URL
    if input_url:
        url_lower = input_url.lower()
        if "rumble.com" in url_lower:
            media_input.source = MediaSource.RUMBLE
        elif "x.com" in url_lower or "twitter.com" in url_lower:
            media_input.source = MediaSource.TWITTER
        elif "tiktok.com" in url_lower or "vm.tiktok.com" in url_lower:
            media_input.source = MediaSource.TIKTOK

    if input_file:
        # Validate file extension, size, etc.
        allowed_extensions = (
            settings.ALLOWED_VIDEO_EXTENSIONS
            if media_type_enum == MediaType.VIDEO
            else settings.ALLOWED_AUDIO_EXTENSIONS
        )

        if not await is_allowed_file(input_file.filename or "", set(allowed_extensions)):
            # Provide more specific error message based on media type
            if media_type_enum == MediaType.VIDEO:
                allowed_exts = settings.ALLOWED_VIDEO_EXTENSIONS
                error_msg = f"Invalid video file type. Please upload a supported video file. Allowed video extensions: {', '.join(['.' + ext for ext in allowed_exts])}"
            else:
                allowed_exts = settings.ALLOWED_AUDIO_EXTENSIONS
                error_msg = f"Invalid audio file type. Please upload a supported audio file. Allowed audio extensions: {', '.join(['.' + ext for ext in allowed_exts])}"

            raise ApplicationException(
                message=error_msg,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        total_bytes = 0
        chunk_size = 1024 * 1024  # 1MB
        while True:
            chunk = await input_file.read(chunk_size)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > settings.MAX_UPLOAD_SIZE:
                raise ApplicationException(
                    message="File size exceeds the maximum allowed limit.",
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                )
        await input_file.seek(0)

        # Use user-specific directory to prevent cross-user overwrites
        upload_dir = Path(settings.UPLOAD_DIR) / "media" / str(current_user.id)
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize and generate unique filename to prevent overwrites
        filename = sanitize_filename(input_file.filename or "upload.bin")
        file_path = get_unique_filename(str(upload_dir), filename)

        async with aiofiles.open(file_path, "wb") as buffer:
            while True:
                chunk = await input_file.read(chunk_size)
                if not chunk:
                    break
                await buffer.write(chunk)

        media_input.file_path = file_path

    if media_type_enum == MediaType.VIDEO:
        job_id = await enqueue_video_processing(media_input, db, model_name=model_name)
    else:
        job_id = await enqueue_audio_processing(media_input, db, model_name=model_name)

    # Attempt quick job cache check
    for _ in range(3):
        await asyncio.sleep(0.1)
        job_data = await get_cache(f"v1.0:media:{job_id}")
        if job_data:
            logger.debug(f"Job {job_id} found in Redis: {job_data}")
            break
    else:
        raise ApplicationException(
            message="Failed to store media information",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Media processing job enqueued",
        data=MediaProcessingResponse(
            job_id=job_id,
            status=MediaProcessingStatus.PENDING,
            message="Media processing job enqueued.",
        ).model_dump(),
    )


@router.get(
    "/media-processing-status/{job_id}",
    operation_id="get_media_processing_status",
    response_model=MediaProcessingStatusResponse,
    responses={
        200: {"description": "Media processing status retrieved successfully"},
        404: {"description": "Not Found"},
        **common_responses,
    },
)
@rate_limit("150/minute")
@handle_route_errors
async def get_media_processing_status_route(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
):
    logger.info(f"Retrieving status for job {job_id}")
    if job_id.startswith("video_"):
        job_status = await get_video_processing_status(job_id, current_user.id)
    else:
        job_status = await get_audio_processing_status(job_id, current_user.id)

    if job_status.status == JobStatus.NOT_FOUND:
        logger.warning(f"Job {job_id} not found")
        return create_response(
            status=ResponseStatus.ERROR,
            message="Job not found",
            data=job_status.model_dump(),
            status_code=status.HTTP_404_NOT_FOUND,
        )

    logger.info(f"Successfully retrieved status for job {job_id}")
    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Media processing status retrieved",
        data=job_status.model_dump(),
        status_code=status.HTTP_200_OK,
    )
