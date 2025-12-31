import json
import logging
from typing import Any, Dict, Optional, Union

from ...config import settings
from ...schemas.job_schema import JobStatusInfo, JobStatusResponse
from ...utils.cache_utils import (
    cache_key_builder,
    get_cache,
    publish_redis_message,
    set_cache,
)
from ...utils.enums import JobStatus, ProcessingStage
from ...utils.error_handlers import ApplicationException

logger = logging.getLogger(__name__)

JOB_STATUS_CHANNEL_PREFIX = "job_status:v1"


def _job_status_channel(job_id: str) -> str:
    return f"{JOB_STATUS_CHANNEL_PREFIX}:{job_id}"


def _job_status_payload(job_info: Union[JobStatusInfo, JobStatusResponse]) -> Dict[str, Any]:
    payload = job_info.model_dump()
    return {
        "job_id": payload.get("job_id"),
        "status": payload.get("status"),
        "progress": payload.get("progress"),
        "stage": payload.get("stage"),
        "message": payload.get("message"),
        "result": payload.get("result"),
        "error": payload.get("error"),
        "user_id": payload.get("user_id"),
    }


async def _publish_job_status(job_info: Union[JobStatusInfo, JobStatusResponse]) -> None:
    channel = _job_status_channel(job_info.job_id)
    payload = _job_status_payload(job_info)
    try:
        published = await publish_redis_message(channel, payload)
        if not published:
            logger.warning(f"Job status publish skipped for channel {channel}")
    except Exception as e:
        logger.warning(f"Job status publish failed for channel {channel}: {str(e)}", exc_info=True)


async def store_job_info(job_id: str, job_info: JobStatusInfo) -> None:
    """
    Store job information in Redis.

    :param job_id: Unique identifier for the job
    :param job_info: Information about the job status
    :raises ApplicationException: If storing job information fails
    """
    try:
        redis_key = cache_key_builder("media", job_id)
        await set_cache(redis_key, job_info.model_dump(), settings.JOB_CACHE_TTL)
        await _publish_job_status(job_info)
    except Exception as e:
        logger.error(f"Failed to store job info: {str(e)}")
        raise ApplicationException("Failed to store job information")


async def get_job_status(job_id: str) -> JobStatusResponse:
    """
    Get the status of a job from Redis.

    :param job_id: Unique identifier for the job
    :return: Current status of the job
    :raises ApplicationException: If retrieving job status fails
    """
    try:
        redis_key = cache_key_builder("media", job_id)
        job_data = await get_cache(redis_key)
        if not job_data:
            return JobStatusResponse(
                job_id=job_id,
                status=JobStatus.NOT_FOUND,
                progress=0,
                message="Job not found",
            )

        # Parse the JSON string into a dictionary
        if isinstance(job_data, str):
            job_data = json.loads(job_data)

        return JobStatusResponse(**job_data)
    except Exception as e:
        logger.error(f"Failed to get job status: {str(e)}")
        raise ApplicationException("Failed to retrieve job status")


async def update_job_status(
    job_id: str,
    status: Union[JobStatus, str],
    progress: int,
    message: str,
    result: Optional[Union[str, Dict[str, Any]]] = None,
    error: Optional[str] = None,
    stage: Optional[Union[ProcessingStage, str]] = None,
) -> None:
    """
    Update the status of a job in Redis.

    :param job_id: Unique identifier for the job
    :param status: New job status
    :param progress: Progress percentage (0-100)
    :param message: Status message
    :param result: Optional result data
    :param error: Optional error message
    :param stage: Optional processing stage (queued, downloading, transcribing, etc.)
    :raises ApplicationException: If updating job status fails
    """
    try:
        redis_key = cache_key_builder("media", job_id)
        job_data = await get_cache(redis_key)
        if not job_data:
            logger.error(f"Job {job_id} not found in Redis")
            return

        # Parse the JSON string into a dictionary if needed
        if isinstance(job_data, str):
            job_data = json.loads(job_data)

        job_info = JobStatusInfo(**job_data)
        status_enum = status if isinstance(status, JobStatus) else JobStatus(status)
        job_info.status = status_enum
        job_info.progress = progress
        job_info.message = message
        if result is not None:
            job_info.result = result if isinstance(result, dict) else {"text": str(result)}
        if error is not None:
            job_info.error = error
        if stage is not None:
            stage_enum = stage if isinstance(stage, ProcessingStage) else ProcessingStage(stage)
            job_info.stage = stage_enum

        await set_cache(redis_key, job_info.model_dump(), settings.JOB_CACHE_TTL)
        await _publish_job_status(job_info)
    except Exception as e:
        logger.error(f"Failed to update job status: {str(e)}")
        raise ApplicationException("Failed to update job status")
