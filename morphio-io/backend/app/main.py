import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi.routing import APIRoute

from .config import settings
from .database import engine


def custom_generate_unique_id(route: APIRoute) -> str:
    """Use operation_id directly instead of FastAPI's default path+method suffix."""
    if route.operation_id:
        return route.operation_id
    return route.name


from .middlewares import (
    CSRFMiddleware,
    SecurityHeadersMiddleware,
    SecurityLoggingMiddleware,
)
from .routes import admin, auth, content, docs, health, logs, media, template, user, web
from .services.template import insert_default_templates
from .utils.create_admin import ensure_admin_user_exists
from .utils.decorators import init_limiter
from .utils.error_handlers import register_exception_handlers
from .utils.logging_config import configure_logging
from .utils.log_context import set_correlation_id, clear_correlation_id
from .utils.alembic_utils import assert_alembic_up_to_date
from .utils.security_logger import setup_security_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application")
    # Setup security logging
    setup_security_logging()
    logger.info("Security logging initialized")

    try:
        # Enforce Alembic up-to-date in production
        try:
            await assert_alembic_up_to_date(engine, enforce=(settings.APP_ENV == "production"))
            logger.info("Alembic revision check passed")
        except Exception as rev_err:
            logger.error(f"Alembic revision check failed: {rev_err}")
            if settings.APP_ENV == "production":
                raise

        # Create admin user if needed
        logger.info("Checking if admin user needs to be created")
        try:
            admin_created = await ensure_admin_user_exists()
            if admin_created:
                logger.info("Admin user confirmed or created successfully")
            else:
                logger.warning(
                    "Admin user check completed but no admin was created - password may not be set"
                )
        except Exception as e:
            logger.error(f"Error ensuring admin user exists: {str(e)}", exc_info=True)

        # Insert default templates
        async with AsyncSession(engine) as session:
            try:
                stats = await insert_default_templates(session)
                if stats["inserted"] == 0 and stats["updated"] == 0 and stats["removed"] == 0:
                    logger.info("Template check completed - all templates are up-to-date")
                else:
                    logger.info("Template synchronization completed successfully")
            except Exception as e:
                logger.error(f"Error inserting default templates: {str(e)}", exc_info=True)

        # Verify MLX Metal on Apple Silicon (optional startup check)
        import platform
        import sys

        if sys.platform == "darwin" and platform.machine() in {"arm64", "aarch64"}:
            try:
                import mlx.core as mx  # type: ignore[import-untyped]

                mx.eval(mx.array([1.0]))
                logger.info("MLX Metal backend verified")
            except ImportError:
                logger.info("MLX not installed, will use CPU for transcription")
            except Exception as e:
                logger.warning(f"MLX Metal check failed: {e}")

        logger.info("Application startup complete")
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}", exc_info=True)
        raise
    yield
    logger.info("Application shutdown complete")


# Configure logging first
configure_logging()

app = FastAPI(
    title="Morphio.io API",
    description="This API will blow your mind",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/api/docs",
    lifespan=lifespan,
    generate_unique_id_function=custom_generate_unique_id,
)

# Add middleware using the standard pattern
# ty false positive: https://github.com/astral-sh/ty/issues/1635
app.add_middleware(
    CORSMiddleware,  # ty: ignore[invalid-argument-type]
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-CSRF-Token",
        "X-Correlation-ID",
        "X-Request-ID",
        "Cache-Control",
        "Pragma",
    ],
)
app.add_middleware(SecurityHeadersMiddleware)  # ty: ignore[invalid-argument-type]
app.add_middleware(SecurityLoggingMiddleware)  # ty: ignore[invalid-argument-type]
app.add_middleware(CSRFMiddleware)  # ty: ignore[invalid-argument-type]

init_limiter(app)
logger.info("CSRF middleware registered (prod-only enforcement for cookie flows)")

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(content.router, prefix="/content", tags=["Content"])
app.include_router(template.router, prefix="/template", tags=["Template"])
app.include_router(user.router, prefix="/user", tags=["User"])
app.include_router(media.router, prefix="/media", tags=["Media Processing"])
app.include_router(docs.router, tags=["Documentation"])
app.include_router(web.router, prefix="/web", tags=["Web Scraping"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])

# Admin sub-routers for extended functionality
from .routes.admin import usage_router as admin_usage_router

app.include_router(admin_usage_router, prefix="/admin", tags=["Admin"])

# Billing routes (Stripe integration)
from .routes import billing

app.include_router(billing.router, tags=["Billing"])

# API Keys routes
from .routes import api_keys

app.include_router(api_keys.router, tags=["API Keys"])

app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(logs.router, prefix="/logs", tags=["Logs"])

# Optional Prometheus metrics endpoint (disabled by default)
if settings.PROMETHEUS_ENABLED:
    from .routes import metrics

    app.include_router(metrics.router)
    logger.info("Prometheus metrics endpoint enabled at /metrics")

register_exception_handlers(app)
security = HTTPBearer()


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """
    Add correlation ID to all requests for tracing.
    Exception handling is delegated to registered exception handlers.
    """
    # Accept incoming correlation ID from client or proxies
    incoming: Optional[str] = request.headers.get("X-Correlation-ID") or request.headers.get(
        "X-Request-ID"
    )
    correlation_id = incoming or str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    set_correlation_id(correlation_id)
    try:
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
    finally:
        clear_correlation_id()


if __name__ == "__main__":
    import uvicorn

    host = "0.0.0.0"
    port = int(os.getenv("APP_PORT", 8000))
    reload = settings.APP_ENV == "development"

    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=settings.UVICORN_WORKERS,
        log_level=settings.LOG_LEVEL.lower(),
    )
