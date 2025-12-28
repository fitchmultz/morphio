# This file handles application exceptions, including custom runtime errors.
# Refactored to remove the local DateTimeEncoder in favor of CustomJSONEncoder from helpers.py.


import asyncio
import json
import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from jwt.exceptions import PyJWTError
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from ..config import settings
from ..schemas.error_schema import ValidationErrorItem
from ..schemas.response_schema import ApiResponse
from ..utils.enums import ResponseStatus
from ..utils.response_utils import CustomJSONEncoder, utc_now

logger = logging.getLogger(__name__)


class ApplicationException(Exception):
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class RateLimitException(ApplicationException):
    def __init__(
        self,
        message: str = "Rate limit exceeded. Please try again later.",
        retry_after: Optional[int] = None,
    ):
        super().__init__(message, status_code=status.HTTP_429_TOO_MANY_REQUESTS)
        self.retry_after = retry_after


def create_error_response(
    status_code: int,
    message: str,
    error_type: str,
    details: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None,
) -> JSONResponse:
    if not settings.DEBUG:
        details = None  # Don't expose details in production

    if request:
        correlation_id = getattr(request.state, "correlation_id", None)
        if correlation_id:
            details = details or {}
            details["correlation_id"] = correlation_id

    error_content = ApiResponse(
        status=ResponseStatus.ERROR,
        message=message,
        data={
            "error_type": error_type,
            "details": details or {},
        },
        timestamp=utc_now(),
    )
    return JSONResponse(
        status_code=status_code,
        content=json.loads(json.dumps(error_content.model_dump(), cls=CustomJSONEncoder)),
    )


def should_include_details(status_code: int) -> bool:
    return status_code >= 500  # Include details for server errors only


def handle_application_exception(
    exc: Exception, request: Optional[Request] = None
) -> ApplicationException:
    def _sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
        sensitive = {
            "authorization",
            "proxy-authorization",
            "cookie",
            "set-cookie",
            "x-api-key",
            "x-auth-token",
            "x-csrftoken",
            "x-csrf-token",
        }
        redacted = {}
        for k, v in headers.items():
            if k.lower() in sensitive:
                redacted[k] = "[REDACTED]"
            else:
                redacted[k] = v
        return redacted

    logger.error(
        f"Application error: {str(exc)}",
        exc_info=True,
        extra={
            "request_method": request.method if request else None,
            "request_url": str(request.url) if request else None,
            "request_headers": _sanitize_headers(dict(request.headers)) if request else None,
        },
    )

    error_message = "An unexpected error occurred. Please try again later."
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    if isinstance(exc, SQLAlchemyError):
        if isinstance(exc, IntegrityError):
            error_message = "A database constraint was violated. Please check your input."
            status_code = status.HTTP_400_BAD_REQUEST
        elif isinstance(exc, OperationalError):
            error_message = "A database operation failed. Please try again later."
        else:
            error_message = "A database error occurred. Please try again later."
    elif isinstance(exc, PyJWTError):
        error_message = "Authentication failed. Please log in again."
        status_code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(exc, asyncio.TimeoutError):
        error_message = "The operation timed out. Please try again later."
        status_code = status.HTTP_504_GATEWAY_TIMEOUT

    return ApplicationException(message=error_message, status_code=status_code)


def add_correlation_id(request: Request, call_next):
    # Deprecated: correlation ID is now handled in app.main middleware
    return call_next(request)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = exc.errors()
        error_items = [
            ValidationErrorItem(loc=error["loc"], msg=error["msg"], type=error["type"])
            for error in errors
        ]
        error_message = " ".join(error["msg"] for error in errors) or "Validation error"

        logger.warning(f"Validation error: {errors}")
        return create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=error_message,
            error_type="RequestValidationError",
            details={"errors": [item.model_dump() for item in error_items]},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return create_error_response(
            status_code=exc.status_code,
            message=exc.detail,
            error_type="HTTPException",
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        return create_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An unexpected error occurred. Please try again later.",
            error_type="UnhandledException",
            request=request,
        )

    @app.exception_handler(RateLimitExceeded)
    @app.exception_handler(RateLimitException)
    async def rate_limit_exception_handler(
        request: Request, exc: RateLimitExceeded | RateLimitException
    ) -> JSONResponse:
        retry_after = getattr(exc, "retry_after", None)
        logger.warning(f"Rate limit exceeded. Retry after: {retry_after}")
        message = "Rate limit exceeded. Please try again later."
        if retry_after:
            message += f" Retry after {retry_after} seconds."
        response = create_error_response(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            message=message,
            error_type="RateLimitError",
            details={"retry_after": retry_after} if retry_after else None,
        )
        if retry_after:
            response.headers["Retry-After"] = str(retry_after)
        return response

    @app.exception_handler(ValueError)
    async def value_error_exception_handler(request: Request, exc: ValueError) -> JSONResponse:
        logger.warning(f"ValueError: {str(exc)}")
        return create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid value provided. Please check your input.",
            error_type="ValueError",
        )

    @app.exception_handler(ApplicationException)
    async def application_exception_handler(
        request: Request, exc: ApplicationException
    ) -> JSONResponse:
        return create_error_response(
            status_code=exc.status_code,
            message=exc.message,
            error_type=exc.__class__.__name__,
        )

    # Correlation ID middleware registered in app.main
