import logging
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.user import User
from ..schemas.media_schema import MediaProcessingStatusResponse
from ..services.generation.core import VALID_GENERATION_MODELS
from ..services.security import get_current_user
from ..services.template import get_template_by_name
from ..services.web import enqueue_web_scraping, get_web_processing_status
from ..utils.decorators import rate_limit, require_auth
from ..utils.enums import JobStatus, ResponseStatus
from ..utils.error_handlers import ApplicationException
from ..utils.response_utils import create_response
from ..utils.route_helpers import handle_route_errors

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/process-web",
    operation_id="process_web",
    response_model=MediaProcessingStatusResponse,
    responses={
        200: {"description": "Enqueued web scraping successfully"},
        400: {"description": "Invalid URL or missing parameters"},
        401: {"description": "Unauthorized"},
    },
)
@rate_limit("100/minute")
@require_auth
@handle_route_errors
async def enqueue_web_scraping_route(
    input_url: str = Form(...),
    template_id: str = Form(...),
    model: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Scrape a webpage at `input_url` and run the text through the LLM+template pipeline.
    Returns a `job_id` that can be polled for status updates.
    """
    try:
        if not input_url.lower().startswith("http://") and not input_url.lower().startswith(
            "https://"
        ):
            input_url = "http://" + input_url

        # Validate model selection
        model_name = model if model and model in VALID_GENERATION_MODELS else ""

        # Normalize template identifier to int or resolved id
        tid: int
        if template_id.isdigit():
            tid = int(template_id)
        else:
            resolved_tid = await get_template_by_name(db, template_id)
            if resolved_tid is None:
                raise ApplicationException(f"Template '{template_id}' not found", status_code=404)
            tid = resolved_tid

        job_id = await enqueue_web_scraping(
            input_url,
            tid,
            user_id=current_user.id,
            db=db,
            model_name=model_name,
        )

        return create_response(
            status=ResponseStatus.SUCCESS,
            message="Web scraping job enqueued",
            data={
                "job_id": job_id,
                "status": "pending",
                "message": "Scraping webpage and generating content...",
            },
            status_code=status.HTTP_200_OK,
        )
    except ApplicationException as ae:
        raise HTTPException(status_code=ae.status_code, detail=ae.message)
    except Exception as e:
        logger.error(f"Unexpected error in enqueue_web_scraping_route: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing the URL",
        )


@router.get(
    "/web-processing-status/{job_id}",
    operation_id="get_web_processing_status",
    response_model=MediaProcessingStatusResponse,
    responses={
        404: {"description": "Job not found"},
        401: {"description": "Unauthorized"},
    },
)
async def get_web_processing_status_route(
    job_id: str, current_user: User = Depends(get_current_user)
):
    """
    Poll the status of the web-scraping job by job_id.
    """
    status_info = await get_web_processing_status(job_id, current_user.id)
    if status_info.status == JobStatus.NOT_FOUND:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Web scraping job status retrieved",
        data=status_info.model_dump(),
        status_code=status.HTTP_200_OK,
    )
