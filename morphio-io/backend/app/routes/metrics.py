"""Prometheus metrics endpoint.

This endpoint exposes application metrics in Prometheus format for scraping.
It is only enabled when PROMETHEUS_ENABLED=true in the configuration.

Metrics are collected automatically by prometheus_client from:
- Default process metrics (CPU, memory, file descriptors)
- Default Python metrics (GC, threads)
- Custom application metrics (request count and latency via metrics middleware)

Usage:
  1. Set PROMETHEUS_ENABLED=true in .env
  2. Configure Prometheus to scrape /metrics endpoint
  3. Metrics will be available at http://localhost:8005/metrics
"""

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter(tags=["metrics"])


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    """Expose Prometheus metrics.

    This endpoint is excluded from OpenAPI schema as it's for
    infrastructure monitoring, not application users.
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
