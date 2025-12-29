"""Admin system health endpoint."""

import asyncio
import logging
import time
from collections.abc import Coroutine
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...database import get_db
from ...models.user import User
from ...schemas.response_schema import ApiResponse
from ...schemas.system_health_schema import (
    HealthComponentOut,
    HealthComponentStatus,
    SystemHealthOut,
    SystemHealthStatus,
)
from ...services.security import get_current_user
from ...utils.cache_utils import test_redis_connection
from ...utils.decorators import require_auth
from ...utils.enums import ResponseStatus
from ...utils.response_utils import create_response
from ...utils.route_helpers import common_responses, handle_route_errors

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Admin"])

_CHECK_TIMEOUT_SECONDS = 3.0


async def _check_database(db: AsyncSession) -> tuple[HealthComponentStatus, str | None]:
    try:
        await db.execute(text("SELECT 1"))
        return HealthComponentStatus.OK, None
    except Exception:
        logger.warning("Database health check failed.", exc_info=True)
        return HealthComponentStatus.ERROR, "Database query failed"


async def _check_redis() -> tuple[HealthComponentStatus, str | None]:
    try:
        is_healthy = await test_redis_connection()
    except Exception:
        logger.warning("Redis health check failed.", exc_info=True)
        return HealthComponentStatus.ERROR, "Redis check failed"
    if is_healthy:
        return HealthComponentStatus.OK, None
    return HealthComponentStatus.ERROR, "Redis unavailable"


async def _check_http_service(name: str, base_url: str) -> tuple[HealthComponentStatus, str | None]:
    url = f"{base_url.rstrip('/')}/health/"
    try:
        async with httpx.AsyncClient(timeout=_CHECK_TIMEOUT_SECONDS) as client:
            response = await client.get(url)
        if 200 <= response.status_code < 300:
            return HealthComponentStatus.OK, None
        logger.warning("Health check returned non-2xx for %s.", name)
        return HealthComponentStatus.ERROR, "Health check failed"
    except Exception:
        logger.warning("Health check request failed for %s.", name, exc_info=True)
        return HealthComponentStatus.ERROR, "Service unreachable"


async def _run_check(
    name: str,
    coro: Coroutine[Any, Any, tuple[HealthComponentStatus, str | None]],
) -> tuple[str, HealthComponentOut]:
    start = time.monotonic()
    try:
        status_value, detail = await asyncio.wait_for(coro, timeout=_CHECK_TIMEOUT_SECONDS)
        latency_ms = int((time.monotonic() - start) * 1000)
        return name, HealthComponentOut(status=status_value, latency_ms=latency_ms, detail=detail)
    except asyncio.TimeoutError:
        latency_ms = int((time.monotonic() - start) * 1000)
        return name, HealthComponentOut(
            status=HealthComponentStatus.ERROR,
            latency_ms=latency_ms,
            detail="Timed out",
        )
    except Exception:
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.warning("Health check failed for %s.", name, exc_info=True)
        return name, HealthComponentOut(
            status=HealthComponentStatus.ERROR,
            latency_ms=latency_ms,
            detail="Check failed",
        )


def _derive_overall_status(components: dict[str, HealthComponentOut]) -> SystemHealthStatus:
    if any(component.status == HealthComponentStatus.ERROR for component in components.values()):
        if (
            components.get("database")
            and components["database"].status == HealthComponentStatus.ERROR
        ):
            return SystemHealthStatus.DOWN
        return SystemHealthStatus.DEGRADED
    return SystemHealthStatus.OK


@router.get(
    "/health",
    operation_id="get_admin_health",
    response_model=ApiResponse[SystemHealthOut],
    responses={403: {"description": "Not authorized"}, **common_responses},
)
@require_auth
@handle_route_errors
async def get_admin_health(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view system health",
        )

    components: dict[str, HealthComponentOut] = {}
    tasks: list[asyncio.Task[tuple[str, HealthComponentOut]]] = [
        asyncio.create_task(_run_check("database", _check_database(db))),
        asyncio.create_task(_run_check("redis", _check_redis())),
    ]

    if settings.WORKER_ML_URL:
        tasks.append(
            asyncio.create_task(
                _run_check("worker_ml", _check_http_service("worker_ml", settings.WORKER_ML_URL))
            )
        )
    else:
        components["worker_ml"] = HealthComponentOut(
            status=HealthComponentStatus.SKIPPED,
            detail="Not configured",
        )

    if settings.CRAWLER_URL:
        tasks.append(
            asyncio.create_task(
                _run_check("crawler", _check_http_service("crawler", settings.CRAWLER_URL))
            )
        )
    else:
        components["crawler"] = HealthComponentOut(
            status=HealthComponentStatus.SKIPPED,
            detail="Not configured",
        )

    for name, result in await asyncio.gather(*tasks):
        components[name] = result

    payload = SystemHealthOut(
        overall_status=_derive_overall_status(components),
        components=components,
    )

    return create_response(
        status=ResponseStatus.SUCCESS,
        message="System health retrieved",
        data=payload.model_dump(),
        status_code=status.HTTP_200_OK,
    )
