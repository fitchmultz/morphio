import functools
import logging
from collections.abc import Callable, Coroutine
from typing import Any, ParamSpec, TypeVar

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.responses import JSONResponse

from .error_handlers import ApplicationException, create_error_response

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")

#: Common responses for 401, 429, 500 so route definitions can avoid repeating them
common_responses = {
    401: {
        "description": "Unauthorized",
        "content": {"application/json": {"example": {"detail": "Not authenticated"}}},
    },
    429: {
        "description": "Too Many Requests",
        "content": {
            "application/json": {
                "example": {"detail": "Rate limit exceeded. Try again in 60 seconds."}
            }
        },
    },
    500: {
        "description": "Internal Server Error",
        "content": {"application/json": {"example": {"detail": "An unexpected error occurred."}}},
    },
}


def handle_route_errors(
    func: Callable[P, Coroutine[Any, Any, R]],
) -> Callable[P, Coroutine[Any, Any, R | JSONResponse]]:
    """
    Decorator that unifies try/except blocks often repeated in route functions.

    It preserves the same error handling flow from the original routes:
      - ApplicationException => custom status/message
      - IntegrityError => 400
      - SQLAlchemyError => 500
      - ValueError => 400
      - HTTPException => re-raise
      - Everything else => 500
    """

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | JSONResponse:
        try:
            return await func(*args, **kwargs)
        except ApplicationException as ae:
            # Typically mapped to a custom status and message
            return create_error_response(
                status_code=ae.status_code,
                message=ae.message,
                error_type="HTTPException",
            )
        except IntegrityError as ie:
            logger.error(f"Integrity error: {ie}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A database integrity error occurred.",
            )
        except SQLAlchemyError as sae:
            logger.error(f"Database error: {sae}", exc_info=True)
            # We raise an ApplicationException here to get the same JSON error shape
            raise ApplicationException(
                message="A database error occurred.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except ValueError as ve:
            logger.warning(f"Value error: {ve}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
        except HTTPException as he:
            # Re-raise so we keep default FastAPI's HTTPException handling
            raise he
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            # Fallback => 500
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred.",
            )

    return wrapper
