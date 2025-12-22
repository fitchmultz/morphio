import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding security headers to all responses.

    This middleware adds essential security headers to all responses while
    avoiding conflicts with headers set by NGINX in production.
    """

    async def dispatch(self, request: Request, call_next):
        """
        Add security headers to the response.

        Args:
            request: The incoming request
            call_next: The next middleware in the chain

        Returns:
            Response with security headers added
        """
        response: Response = await call_next(request)

        # Keep only essential security headers that don't conflict with NGINX CORS
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=()"
        )
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"

        # API-safe Content Security Policy (no inline content served)
        # This is conservative for JSON APIs and won't interfere with CORS
        csp = (
            "default-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'none'; "
            "form-action 'self'; "
            "connect-src 'self'"
        )
        response.headers["Content-Security-Policy"] = csp

        logger.debug("Security headers added to response")
        return response
