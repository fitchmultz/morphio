import logging

from app.utils.cache_utils import test_redis_connection
from app.utils.response_utils import ResponseStatus, create_response
from fastapi import APIRouter, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import engine

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


@router.get("/db", tags=["Health"])
async def health_db():
    logger = logging.getLogger(__name__)
    try:
        async with AsyncSession(engine) as session:
            await session.execute(text("SELECT 1"))
        return create_response(
            status=ResponseStatus.SUCCESS,
            message="Database is healthy",
            data=None,
            status_code=status.HTTP_200_OK,
        )
    except SQLAlchemyError as exc:
        logger.error(f"Database health check failed: {exc}", exc_info=True)
        return create_response(
            status=ResponseStatus.ERROR,
            message="Database is unavailable",
            data=None,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@router.get("/redis", tags=["Health"])
async def health_redis():
    logger = logging.getLogger(__name__)
    try:
        is_healthy = await test_redis_connection()
    except Exception as exc:
        logger.error(f"Redis health check failed: {exc}", exc_info=True)
        is_healthy = False

    if is_healthy:
        return create_response(
            status=ResponseStatus.SUCCESS,
            message="Redis is healthy",
            data=None,
            status_code=status.HTTP_200_OK,
        )

    return create_response(
        status=ResponseStatus.ERROR,
        message="Redis is unavailable",
        data=None,
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )
