import logging
from typing import TYPE_CHECKING

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

if TYPE_CHECKING:
    from ..config import Settings

logger = logging.getLogger(__name__)


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Middleware for CSRF protection.

    This middleware validates that CSRF tokens are present and match for
    state-changing requests (POST, PUT, DELETE, PATCH). The middleware compares
    the token from the cookies and the X-CSRF-Token header to prevent CSRF attacks.

    Cookie-auth endpoints (login, register, logout, refresh-token) require CSRF
    protection to prevent login CSRF attacks.
    """

    # Paths that never need CSRF (only token-fetching and health checks)
    EXEMPT_PATHS = {
        "/auth/csrf-token",
        "/health",
        "/health/",
    }

    # Paths that set/use cookies and MUST have CSRF protection
    # These are protected regardless of whether a refresh_token cookie exists
    # Note: /auth/register is NOT included - registration CSRF has no meaningful attack vector
    # (attacker gains nothing by making victim register a new account)
    COOKIE_AUTH_PATHS = {
        "/auth/login",
        "/auth/logout",
        "/auth/refresh-token",
    }

    # HTTP methods that modify state and require CSRF protection
    PROTECTED_METHODS = ["POST", "PUT", "DELETE", "PATCH"]

    async def dispatch(self, request: Request, call_next):
        """
        Check CSRF token validity for protected routes and methods.

        Args:
            request: The incoming request
            call_next: The next middleware in the chain

        Returns:
            Response: Either the original response if valid or a 403 if invalid
        """
        path = request.url.path

        # Skip CSRF validation for non-mutation methods or exempt paths
        if request.method not in self.PROTECTED_METHODS or self._is_path_exempt(path):
            return await call_next(request)

        # Only enforce CSRF in production to reduce dev/CI friction
        from ..config import settings  # local import to avoid cycles

        if settings.APP_ENV != "production":
            return await call_next(request)

        # Scope CSRF checks to cookie-auth flows only:
        # - If Authorization Bearer token is present, skip CSRF (token-based API)
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            return await call_next(request)

        # Determine if this is a cookie-auth path that always needs CSRF protection
        is_cookie_auth_path = path in self.COOKIE_AUTH_PATHS

        # For cookie-auth paths: always require CSRF (prevents login CSRF)
        # For other paths: only require CSRF if refresh_token cookie is present
        refresh_cookie = request.cookies.get("refresh_token")
        if not is_cookie_auth_path and not refresh_cookie:
            return await call_next(request)

        # Validate Origin header for cookie-auth paths (additional protection)
        if is_cookie_auth_path:
            origin = request.headers.get("origin")
            if origin and not self._is_trusted_origin(origin, settings):
                logger.warning(f"CSRF: Untrusted origin {origin} for {path}")
                return Response(
                    content='{"status":"error","message":"Untrusted origin"}',
                    status_code=403,
                    media_type="application/json",
                )

        # Get the CSRF token from the headers and cookies
        csrf_token_header = request.headers.get("X-CSRF-Token")
        csrf_token_cookie = request.cookies.get("csrf_token")

        # Enhanced debugging for CSRF validation
        self._log_csrf_details(request, csrf_token_header, csrf_token_cookie)

        # Require both header and cookie when refresh cookies are used

        # Validate that both tokens exist and match
        if not self._are_tokens_valid(csrf_token_header, csrf_token_cookie):
            logger.warning(
                f"CSRF validation failed for {request.url.path}. "
                f"Header token: {'Present' if csrf_token_header else 'Missing'}, "
                f"Cookie token: {'Present' if csrf_token_cookie else 'Missing'}, "
                "Match: {match_status}".format(
                    match_status=(
                        "Yes"
                        if (
                            csrf_token_header
                            and csrf_token_cookie
                            and csrf_token_header == csrf_token_cookie
                        )
                        else ("No" if (csrf_token_header and csrf_token_cookie) else "N/A")
                    )
                )
            )
            return Response(
                content='{"status":"error","message":"CSRF token validation failed"}',
                status_code=403,
                media_type="application/json",
            )

        return await call_next(request)

    def _is_path_exempt(self, path: str) -> bool:
        """Check if the path is exempt from CSRF protection."""
        # Use exact matching for security - endswith is too permissive
        if path in self.EXEMPT_PATHS:
            return True
        # Allow health check prefixes
        if path.startswith("/health"):
            return True
        # Allow OpenAPI/docs paths
        if path.startswith("/docs") or path.startswith("/openapi"):
            return True
        return False

    def _is_trusted_origin(self, origin: str, settings: "Settings") -> bool:
        """Check if the origin is in the trusted list."""
        from urllib.parse import urlparse

        try:
            parsed_origin = urlparse(origin)
            origin_host = parsed_origin.netloc.lower()
        except (TypeError, AttributeError) as e:
            logger.warning(f"Could not parse origin '{origin}': {e}")
            return False

        # Check against CORS origins
        for allowed_origin in settings.CORS_ORIGINS:
            try:
                allowed_parsed = urlparse(allowed_origin)
                if allowed_parsed.netloc.lower() == origin_host:
                    return True
            except (TypeError, AttributeError) as e:
                logger.warning(f"Could not parse allowed_origin '{allowed_origin}': {e}")
                continue

        return False

    def _are_tokens_valid(self, header_token: str | None, cookie_token: str | None) -> bool:
        """Validate that both tokens exist and match."""
        return (
            header_token is not None and cookie_token is not None and header_token == cookie_token
        )

    def _log_csrf_details(
        self, request: Request, header_token: str | None, cookie_token: str | None
    ) -> None:
        """Log detailed information about the CSRF check for debugging."""

        def _sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
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
            return {k: ("[REDACTED]" if k.lower() in sensitive else v) for k, v in headers.items()}

        logger.debug(f"CSRF check for {request.url.path}")
        logger.debug(f"Request Origin: {request.headers.get('origin')}")
        logger.debug(f"Request Referer: {request.headers.get('referer')}")
        logger.debug(f"All Headers: {_sanitize_headers(dict(request.headers))}")
        logger.debug(f"All Cookies: { {k: '[REDACTED]' for k in request.cookies.keys()} }")
        logger.debug(f"CSRF Header Token: {'present' if header_token else 'missing'}")
        logger.debug(f"CSRF Cookie Token: {'present' if cookie_token else 'missing'}")
