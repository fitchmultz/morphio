import logging

from app.utils.response_utils import ResponseStatus, create_response
from fastapi import APIRouter, status

router = APIRouter()


@router.get("/", tags=["Health"])
async def health_check():
    logger = logging.getLogger(__name__)
    logger.info("Health check endpoint called")
    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Service is healthy",
        data=None,
        status_code=status.HTTP_200_OK,
    )
