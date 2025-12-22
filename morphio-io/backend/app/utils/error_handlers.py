# This file handles application exceptions, including custom and OpenAI-based errors.
# Refactored to remove the local DateTimeEncoder in favor of CustomJSONEncoder from helpers.py.


import asyncio
import json
import logging
from typing import Any, Dict, Optional, Union

from fastapi import FastAPI, Request, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from jwt.exceptions import PyJWTError
from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    PermissionDeniedError,
    RateLimitError,
)
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from ..config import settings
from ..schemas.error_schema import ValidationErrorItem
from ..schemas.response_schema import ApiResponse
from ..utils.enums import ResponseStatus
from ..utils.response_utils import CustomJSONEncoder, utc_now

logger = logging.getLogger(__name__)

OPENAI_ERROR_MAPPING: Dict[type, tuple[int, str]] = {
    AuthenticationError: (
        status.HTTP_401_UNAUTHORIZED,
        "Authentication failed with OpenAI API.",
    ),
    RateLimitError: (
        status.HTTP_429_TOO_MANY_REQUESTS,
        "OpenAI API rate limit exceeded.",
    ),
    APIConnectionError: (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "Failed to connect to OpenAI API.",
    ),
    APITimeoutError: (
        status.HTTP_504_GATEWAY_TIMEOUT,
        "Request to OpenAI API timed out.",
    ),
}


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


def handle_openai_exception(exc: Exception) -> ApplicationException:
    logger.error(f"OpenAI API error: {str(exc)}", exc_info=True)
    error_info = OPENAI_ERROR_MAPPING.get(
        type(exc),
        (
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "An unexpected error occurred with the OpenAI API.",
        ),
    )
    return ApplicationException(message=error_info[1], status_code=error_info[0])


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

    @app.exception_handler(AuthenticationError)
    async def authentication_exception_handler(
        request: Request, exc: AuthenticationError
    ) -> JSONResponse:
        logger.error("Authentication failed with OpenAI API")
        return create_error_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message="Authentication failed. Check your OpenAI API key.",
            error_type="AuthenticationError",
        )

    @app.exception_handler(APIConnectionError)
    async def api_connection_exception_handler(
        request: Request, exc: APIConnectionError
    ) -> JSONResponse:
        logger.error("Failed to connect to OpenAI API")
        return create_error_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="Failed to connect to OpenAI's API. Please try again later.",
            error_type="APIConnectionError",
        )

    @app.exception_handler(RateLimitExceeded)
    @app.exception_handler(RateLimitError)
    @app.exception_handler(RateLimitException)
    async def rate_limit_exception_handler(
        request: Request, exc: Union[RateLimitExceeded, RateLimitError, RateLimitException]
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

    @app.exception_handler(BadRequestError)
    async def bad_request_exception_handler(request: Request, exc: BadRequestError) -> JSONResponse:
        logger.error(f"Bad request sent to the API: {str(exc)}")
        return create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid request. Please check your input and try again.",
            error_type="BadRequestError",
        )

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

    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
        logger.error(f"OpenAI API error: {str(exc)}")
        return create_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An error occurred with the OpenAI API. Please try again later.",
            error_type="APIError",
        )

    @app.exception_handler(InternalServerError)
    async def internal_server_error_handler(
        request: Request, exc: InternalServerError
    ) -> JSONResponse:
        logger.error(f"OpenAI Internal Server Error: {str(exc)}")
        return create_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An internal server error occurred. Please try again later.",
            error_type="InternalServerError",
        )

    @app.exception_handler(APITimeoutError)
    async def api_timeout_error_handler(request: Request, exc: APITimeoutError) -> JSONResponse:
        logger.error(f"OpenAI API Timeout Error: {str(exc)}")
        return create_error_response(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            message="The request to OpenAI API timed out. Please try again later.",
            error_type="APITimeoutError",
        )

    @app.exception_handler(PermissionDeniedError)
    async def permission_denied_error_handler(
        request: Request, exc: PermissionDeniedError
    ) -> JSONResponse:
        logger.error(f"Permission Denied Error: {str(exc)}")
        return create_error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="You don't have permission to perform this action.",
            error_type="PermissionDeniedError",
        )

    # Correlation ID middleware registered in app.main
