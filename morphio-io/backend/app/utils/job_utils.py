import asyncio
import logging
from collections.abc import Callable
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.job_schema import JobStatusInfo
from ..services.job import store_job_info, update_job_status
from ..utils.enums import JobStatus, ProcessingStage

logger = logging.getLogger(__name__)

# Module-level set to track running tasks (prevents garbage collection)
_running_tasks: set[asyncio.Task[None]] = set()


async def enqueue_task(
    process_func: Callable,
    input_data: dict,
    db: AsyncSession,
    user_id: int,
    model_name: str = "",
) -> str:
    """Generic function to enqueue an async processing task."""
    job_id = str(uuid4())
    logger.info(f"Enqueueing job {job_id}")

    job_info = JobStatusInfo(
        job_id=job_id,
        status=JobStatus.PENDING,
        progress=0,
        message="Job queued",
        user_id=user_id,
        chosen_model=model_name,
    )
    await store_job_info(job_id, job_info)

    async def run_job():
        try:
            # Pass input_data as-is, including anonymize if present
            await process_func(input_data, job_id, db, user_id)
        except Exception as e:
            logger.error(f"Error in job {job_id}: {str(e)}", exc_info=True)
            await update_job_status(
                job_id,
                JobStatus.FAILED.value,
                100,
                f"Unexpected error: {str(e)}",
                error=str(e),
                stage=ProcessingStage.FAILED,
            )

    task = asyncio.create_task(run_job(), name=f"processing_{job_id}")
    _running_tasks.add(task)
    task.add_done_callback(_running_tasks.discard)

    return job_id
