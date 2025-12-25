import logging
import time
from typing import Awaitable, Callable

from prometheus_client import Counter, Histogram
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)


async def prometheus_metrics_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    start_time = time.perf_counter()
    status_code = 500
    response: Response | None = None

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        duration = time.perf_counter() - start_time
        try:
            REQUEST_COUNT.labels(
                method=request.method,
                path=request.url.path,
                status=str(status_code),
            ).inc()
            REQUEST_LATENCY.labels(
                method=request.method,
                path=request.url.path,
            ).observe(duration)
        except Exception:
            logger.debug("Failed to record Prometheus metrics", exc_info=True)
