"""Purpose: Provide reusable request decorators and limiter setup for backend endpoints.
Responsibilities: Configure rate limiting, auth-adjacent wrappers, and shared decorator behavior.
Scope: Backend utility layer consumed by route modules that need rate limiting or response wrappers.
Usage: Imported by route handlers and application startup to attach limiter behavior.
Invariants/Assumptions: Development fallbacks may degrade to in-memory rate limiting without surfacing noisy warnings intended only for production incidents.
"""

import functools
import json
import logging
import time
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any, ParamSpec, Protocol, TypeVar

import redis
from fastapi import FastAPI, HTTPException, Request, status
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from ..config import settings
from ..schemas.cache_schema import CacheConfig
from ..schemas.error_schema import RetryConfig
from ..schemas.rate_limit_schema import RateLimitConfig
from .cache_utils import get_redis_data, is_redis_available, set_redis_data
from .error_handlers import ApplicationException, create_error_response

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


class RateLimitProtocol(Protocol):
    """Protocol for rate limit function signature."""

    def __call__(self, request: Request, limit: str) -> Awaitable[None]: ...


limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL,
)


async def _noop_ratelimit(request: Request, limit: str) -> None:
    """No-op rate limit function for when limiter doesn't have ratelimit method."""
    return None


# Module-level typed ratelimit function
_ratelimit_func: RateLimitProtocol = _noop_ratelimit

try:
    redis_client = redis.Redis.from_url(settings.REDIS_URL)
    redis_client.ping()
    logger.info("Redis connection established successfully")
    # Try to get the ratelimit method from limiter if available
    if hasattr(limiter, "ratelimit"):
        _ratelimit_func = getattr(limiter, "ratelimit")
except (redis.ConnectionError, redis.exceptions.TimeoutError) as e:
    log = logger.warning if settings.APP_ENV == "production" else logger.info
    log(f"Failed to connect to Redis ({e}). Using in-memory rate limiting.")
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri="memory://",
    )
    # Enable rate limiting with in-memory storage
    if hasattr(limiter, "ratelimit"):
        _ratelimit_func = getattr(limiter, "ratelimit")


def _rate_limit_exceeded_handler(request: Request, exc: Exception) -> JSONResponse:
    retry_after = getattr(exc, "retry_after", None)
    return create_error_response(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        message=(
            f"Rate limit exceeded. Try again in {retry_after} seconds."
            if retry_after is not None
            else "Rate limit exceeded. Try again later."
        ),
        error_type="RateLimitExceeded",
        details={"retry_after": retry_after} if retry_after is not None else {},
        request=request,
    )


def init_limiter(app: FastAPI) -> Limiter:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    return limiter


def require_auth(
    func: Callable[P, Coroutine[Any, Any, R]],
) -> Callable[P, Coroutine[Any, Any, R | JSONResponse]]:
    """Decorator that requires authentication via current_user in kwargs."""

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | JSONResponse:
        if "current_user" not in kwargs or not kwargs["current_user"]:
            logger.warning("Authentication required")
            return create_error_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Authentication required",
                error_type="AuthenticationError",
            )
        return await func(*args, **kwargs)

    return wrapper


def rate_limit(
    limit: str,
) -> Callable[
    [Callable[P, Coroutine[Any, Any, R]]],
    Callable[P, Coroutine[Any, Any, R | JSONResponse]],
]:
    """Rate limiting decorator using slowapi."""
    config = RateLimitConfig(limit=limit)

    def decorator(
        func: Callable[P, Coroutine[Any, Any, R]],
    ) -> Callable[P, Coroutine[Any, Any, R | JSONResponse]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | JSONResponse:
            if not settings.RATE_LIMITING_ENABLED:
                return await func(*args, **kwargs)

            # Try to find Request in args or kwargs first
            request = next((arg for arg in args if isinstance(arg, Request)), None)
            if not request and "request" in kwargs:
                request = kwargs["request"]
            # If still not found, try to get from contextvars (FastAPI stores request there)
            if not request:
                try:
                    from contextvars import copy_context

                    # FastAPI/Starlette stores request in contextvars
                    ctx = copy_context()
                    for var_name, var_value in ctx.items():
                        if isinstance(var_value, Request):
                            request = var_value
                            break
                except Exception:
                    pass
            # Last resort: try to get from kwargs using Depends pattern
            if not request:
                try:
                    from starlette.requests import Request as StarletteRequest

                    request = next((arg for arg in args if isinstance(arg, StarletteRequest)), None)
                except ImportError:
                    pass
            if not isinstance(request, Request):
                logger.error("Couldn't find request object in function arguments or context")
                return create_error_response(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message="Internal server error",
                    error_type="InternalServerError",
                )

            # request is now narrowed to Request via isinstance check
            try:
                await _ratelimit_func(request, config.limit)
                return await func(*args, **kwargs)
            except RateLimitExceeded as exc:
                logger.warning("Rate limit exceeded")
                retry_after = getattr(exc, "retry_after", None)
                return create_error_response(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    message=(
                        f"Rate limit exceeded. Try again in {retry_after} seconds."
                        if retry_after is not None
                        else "Rate limit exceeded. Try again later."
                    ),
                    error_type="RateLimitExceeded",
                    details={"retry_after": retry_after} if retry_after is not None else {},
                    request=request,
                )

        return wrapper

    return decorator


def async_retry(
    max_retries: int = 3, delay: int = 1
) -> Callable[
    [Callable[P, Coroutine[Any, Any, R]]],
    Callable[P, Coroutine[Any, Any, R]],
]:
    """Retry decorator with exponential backoff."""
    config = RetryConfig(max_retries=max_retries, delay=delay)

    def decorator(
        func: Callable[P, Coroutine[Any, Any, R]],
    ) -> Callable[P, Coroutine[Any, Any, R]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            for attempt in range(config.max_retries):
                try:
                    return await func(*args, **kwargs)
                except (HTTPException, ApplicationException) as ae:
                    # Do not retry on these exceptions
                    raise ae
                except Exception as e:
                    func_name = getattr(func, "__name__", "unknown")
                    if attempt == config.max_retries - 1:
                        logger.error(
                            f"Function {func_name} failed after {config.max_retries} retries. "
                            f"Error: {str(e)}"
                        )
                        raise ApplicationException(
                            message=f"Operation failed after {config.max_retries} attempts",
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        )
                    logger.warning(
                        f"Retrying {func_name} (attempt {attempt + 1}/{config.max_retries}). "
                        f"Error: {str(e)}"
                    )
                    await run_in_threadpool(time.sleep, config.delay * (2**attempt))
            # This should never be reached, but satisfies type checker
            raise ApplicationException(
                message="Retry logic error",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return wrapper

    return decorator


def cache(
    expire: int = 300,
) -> Callable[
    [Callable[P, Coroutine[Any, Any, R]]],
    Callable[P, Coroutine[Any, Any, R]],
]:
    """
    Caching decorator that includes 'current_user.id' (if present) in the cache key.
    This prevents data leakage between different authenticated users.
    """
    config = CacheConfig(expire=expire)

    def decorator(
        func: Callable[P, Coroutine[Any, Any, R]],
    ) -> Callable[P, Coroutine[Any, Any, R]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            if not is_redis_available():
                return await func(*args, **kwargs)

            request = next((arg for arg in args if isinstance(arg, Request)), None)
            if not request:
                return await func(*args, **kwargs)

            user_id_str = "anon"
            current_user = kwargs.get("current_user")
            if current_user and hasattr(current_user, "id"):
                user_id_str = str(current_user.id)

            func_name = getattr(func, "__name__", "unknown")
            cache_key = (
                f"{config.key_prefix}{func_name}:"
                f"{request.url.path}:"
                f"{request.query_params}:"
                f"user_id={user_id_str}"
            )

            cached_result = await get_redis_data(cache_key)
            if cached_result:
                # Cached result is JSON-serialized output from this decorator.
                return json.loads(cached_result)

            result = await func(*args, **kwargs)
            await set_redis_data(cache_key, json.dumps(result), config.expire)
            return result

        return wrapper

    return decorator
