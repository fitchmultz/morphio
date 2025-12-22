import logging

from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas.media_schema import MediaProcessingStatusResponse
from ...utils.error_handlers import ApplicationException
from ...utils.job_utils import enqueue_task
from ..job import get_job_status

logger = logging.getLogger(__name__)


async def enqueue_web_scraping(
    url: str,
    template_id: str | int,
    user_id: int,
    db: AsyncSession,
    model_name: str = "",
) -> str:
    """Enqueue web scraping and generation task."""
    from .processing import (  # Import here to avoid circular imports
        scrape_and_generate_web,
    )

    input_data = {"url": url, "template_id": template_id}
    return await enqueue_task(scrape_and_generate_web, input_data, db, user_id, model_name)


async def get_web_processing_status(job_id: str, user_id: int) -> MediaProcessingStatusResponse:
    """Get the status of a web processing job."""
    status = await get_job_status(job_id)
    if status.user_id != user_id:
        raise ApplicationException("Not authorized to access this job", status_code=403)
    return MediaProcessingStatusResponse(
        job_id=job_id,
        status=status.status,
        progress=status.progress,
        message=status.message,
        result=status.result if isinstance(status.result, (str, dict)) else None,
        error=status.error,
    )
