import json
import logging
from typing import Any, Dict, Optional, Union

from ...config import settings
from ...schemas.job_schema import JobStatusInfo, JobStatusResponse
from ...utils.cache_utils import cache_key_builder, get_cache, set_cache
from ...utils.enums import JobStatus, ProcessingStage
from ...utils.error_handlers import ApplicationException

logger = logging.getLogger(__name__)


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
    except Exception as e:
        logger.error(f"Failed to update job status: {str(e)}")
        raise ApplicationException("Failed to update job status")
