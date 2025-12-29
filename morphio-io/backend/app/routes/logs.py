import logging
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, File, Path as PathParam, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..models.user import User
from ..schemas.logs_schema import LogsProcessingResponse, LogsProcessingStatusResponse
from ..schemas.response_schema import ApiResponse
from ..services.logs import (
    enqueue_logs_processing,
    enqueue_splunk_config_processing,
    get_logs_processing_status,
)
from ..services.security import get_current_user
from ..utils.decorators import rate_limit, require_auth
from ..utils.enums import JobStatus, ResponseStatus
from ..utils.error_handlers import ApplicationException
from ..utils.file_utils import get_file_extension, is_allowed_file, sanitize_filename
from ..utils.response_utils import create_response
from ..utils.route_helpers import common_responses, handle_route_errors

router = APIRouter(tags=["Logs"])
logger = logging.getLogger(__name__)

ALLOWED_LOG_EXTENSIONS = {ext.lower() for ext in settings.ALLOWED_LOG_EXTENSIONS}


@router.post(
    "/process-logs",
    operation_id="process_logs",
    response_model=ApiResponse[LogsProcessingResponse],
    responses={
        **common_responses,
        200: {
            "description": "Log processing job enqueued successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Log processing job enqueued",
                        "data": {
                            "job_id": "123e4567-e89b-12d3-a456-426614174000",
                            "status": "pending",
                            "message": "Log processing job enqueued.",
                        },
                    }
                }
            },
        },
        400: {
            "description": "Bad Request",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "message": "Invalid file type. Only .log, .txt files are supported.",
                        "data": {"error_type": "ApplicationException", "details": {}},
                    }
                }
            },
        },
        401: {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "message": "Not authenticated",
                        "data": {"error_type": "HTTPException", "details": {}},
                    }
                }
            },
        },
        413: {
            "description": "Payload Too Large",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "message": "Log file exceeds maximum upload size.",
                        "data": {"error_type": "ApplicationException", "details": {}},
                    }
                }
            },
        },
    },
)
@rate_limit("100/minute")
@require_auth
@handle_route_errors
async def process_logs(
    request: Request,
    log_file: UploadFile = File(
        ...,
        description="Log file to process",
        examples=["app.log"],
    ),
    anonymize: bool = Query(
        False,
        description="Anonymize sensitive data before processing",
        examples=[False],
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enqueue a log file for processing and return a job ID."""
    logger.debug(f"Received log upload request from user {current_user.id}, anonymize={anonymize}")

    if not log_file:
        logger.warning("No log_file provided in request")
        raise ApplicationException(
            "Log file is required. Please upload a valid file.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    original_filename = log_file.filename
    sanitized_filename = sanitize_filename(original_filename or "upload.log")

    if not await is_allowed_file(sanitized_filename.lower(), ALLOWED_LOG_EXTENSIONS):
        file_extension = await get_file_extension(sanitized_filename)
        logger.warning(
            f"Invalid file type uploaded: filename='{original_filename}', "
            f"sanitized='{sanitized_filename}', extension='{file_extension}'. "
            f"Allowed extensions: {ALLOWED_LOG_EXTENSIONS}"
        )
        raise ApplicationException(
            f"Invalid file type. Only {', '.join(['.' + ext for ext in settings.ALLOWED_LOG_EXTENSIONS])} files are supported.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / sanitized_filename

    max_upload_size = settings.MAX_UPLOAD_SIZE
    total_size = 0

    try:
        async with aiofiles.open(file_path, "wb") as buffer:
            while True:
                chunk = await log_file.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > max_upload_size:
                    raise ApplicationException(
                        "Log file exceeds maximum upload size.",
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    )
                await buffer.write(chunk)
    except ApplicationException:
        if file_path.exists():
            file_path.unlink()
        raise
    except Exception as e:
        logger.error(f"Failed to save file {sanitized_filename}: {str(e)}")
        raise ApplicationException(
            "Failed to save uploaded file.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    job_id = await enqueue_logs_processing(file_path, current_user.id, db, anonymize=anonymize)
    response_data = LogsProcessingResponse(
        job_id=job_id,
        status="pending",
        message="Log processing job enqueued.",
    )
    logger.info(f"Log processing job enqueued: {job_id} for user {current_user.id}")
    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Log processing job enqueued",
        data=response_data.model_dump(),
        status_code=status.HTTP_200_OK,
    )


@router.get(
    "/logs-processing-status/{job_id}",
    operation_id="get_logs_processing_status",
    response_model=ApiResponse[LogsProcessingStatusResponse],
    responses={
        **common_responses,
        200: {
            "description": "Log processing status retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Log processing status retrieved",
                        "data": {
                            "job_id": "123e4567-e89b-12d3-a456-426614174000",
                            "status": "completed",
                            "progress": 100,
                            "message": "Log summary generated and saved",
                            "result": {
                                "summary": "Summary content here",
                                "title": "Log Summary",
                                "content_id": 1,
                                "user_id": 1,
                                "template_id": "log-summary",
                            },
                            "error": None,
                        },
                    }
                }
            },
        },
        404: {
            "description": "Job not found",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "message": "Job not found",
                        "data": {
                            "job_id": "123e4567-e89b-12d3-a456-426614174000",
                            "status": "not_found",
                            "progress": 0,
                            "stage": None,
                            "message": None,
                            "result": None,
                            "error": None,
                        },
                    }
                }
            },
        },
        401: {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "message": "Not authenticated",
                        "data": {"error_type": "HTTPException", "details": {}},
                    }
                }
            },
        },
    },
)
@rate_limit("150/minute")
@handle_route_errors
async def get_logs_processing_status_route(
    job_id: str = PathParam(
        ...,
        description="Log processing job ID",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the status of a log processing job."""
    logger.info(f"Retrieving status for job {job_id}")

    job_status = await get_logs_processing_status(job_id, current_user.id, db)

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
        message="Log processing status retrieved",
        data=job_status.model_dump(),
        status_code=status.HTTP_200_OK,
    )


@router.post(
    "/generate-splunk-config",
    operation_id="generate_splunk_config",
    response_model=ApiResponse[LogsProcessingResponse],
    responses={
        200: {
            "description": "Splunk config generation job enqueued successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Splunk config generation job enqueued",
                        "data": {
                            "job_id": "123e4567-e89b-12d3-a456-426614174000",
                            "status": "pending",
                            "message": "Splunk config generation job enqueued.",
                        },
                    }
                }
            },
        },
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        **common_responses,
    },
)
@rate_limit("100/minute")
@require_auth
@handle_route_errors
async def generate_splunk_config(
    request: Request,
    log_file: UploadFile = File(...),
    anonymize: bool = Query(False, description="Anonymize sensitive data before processing"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enqueue a log file sample for Splunk config generation and return a job ID."""
    logger.debug(
        f"Received Splunk config generation request from user {current_user.id}, "
        f"anonymize={anonymize}"
    )

    if not log_file:
        logger.warning("No log_file provided in request")
        raise ApplicationException(
            "Log file is required. Please upload a valid file.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    original_filename = log_file.filename
    sanitized_filename = sanitize_filename(original_filename or "upload.log")

    if not await is_allowed_file(sanitized_filename.lower(), ALLOWED_LOG_EXTENSIONS):
        file_extension = await get_file_extension(sanitized_filename)
        logger.warning(
            f"Invalid file type uploaded: filename='{original_filename}', "
            f"sanitized='{sanitized_filename}', extension='{file_extension}'. "
            f"Allowed extensions: {ALLOWED_LOG_EXTENSIONS}"
        )
        raise ApplicationException(
            f"Invalid file type. Only {', '.join(['.' + ext for ext in settings.ALLOWED_LOG_EXTENSIONS])} files are supported.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / sanitized_filename

    max_upload_size = settings.MAX_UPLOAD_SIZE
    total_size = 0

    try:
        async with aiofiles.open(file_path, "wb") as buffer:
            while True:
                chunk = await log_file.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > max_upload_size:
                    raise ApplicationException(
                        "Log file exceeds maximum upload size.",
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    )
                await buffer.write(chunk)
    except ApplicationException:
        if file_path.exists():
            file_path.unlink()
        raise
    except Exception as e:
        logger.error(f"Failed to save file {sanitized_filename}: {str(e)}")
        raise ApplicationException(
            "Failed to save uploaded file.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    job_id = await enqueue_splunk_config_processing(
        file_path, current_user.id, db, anonymize=anonymize
    )
    response_data = LogsProcessingResponse(
        job_id=job_id,
        status="pending",
        message="Splunk config generation job enqueued.",
    )
    logger.info(f"Splunk config generation job enqueued: {job_id} for user {current_user.id}")
    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Splunk config generation job enqueued",
        data=response_data.model_dump(),
        status_code=status.HTTP_200_OK,
    )


@router.get(
    "/config",
    operation_id="get_log_config",
    response_model=ApiResponse[dict],
    responses={
        200: {
            "description": "Log file configuration",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Log file configuration",
                        "data": {
                            "allowed_extensions": ["csv", "json", "log", "md", "txt"],
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
async def get_log_file_configuration():
    """Get log file configuration including allowed extensions."""
    logger.info("Retrieving log file configuration")

    config = {
        "allowed_extensions": settings.ALLOWED_LOG_EXTENSIONS,
        "max_upload_size": settings.MAX_UPLOAD_SIZE,
    }

    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Log file configuration",
        data=config,
        status_code=status.HTTP_200_OK,
    )
