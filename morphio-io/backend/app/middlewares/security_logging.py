import time
from typing import Dict, List, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from ..utils.security_logger import SECURITY_AUDIT, log_security_event


class SecurityLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging security-relevant information for all requests.

    This middleware logs:
    - Request metadata (method, path, query params, headers)
    - Response status code and timing
    - User information when available
    """

    def __init__(
        self,
        app,
        exclude_paths: Optional[List[str]] = None,
        exclude_extensions: Optional[List[str]] = None,
        sensitive_headers: Optional[List[str]] = None,
    ):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/api/docs", "/openapi.json"]
        self.exclude_extensions = exclude_extensions or [
            ".js",
            ".css",
            ".png",
            ".jpg",
            ".ico",
            ".svg",
        ]
        self.sensitive_headers = sensitive_headers or [
            "authorization",
            "x-api-key",
            "cookie",
            "x-csrftoken",
            "x-csrf-token",
        ]

    async def dispatch(self, request: Request, call_next):
        """Process the request, log security information, and pass to the next middleware."""
        start_time = time.time()

        # Skip logging for excluded paths
        path = request.url.path

        # Skip logging for static files and health checks
        if any(path.startswith(exclude) for exclude in self.exclude_paths) or any(
            path.endswith(ext) for ext in self.exclude_extensions
        ):
            return await call_next(request)

        # Extract request information
        method = request.method
        query_params = dict(request.query_params)

        # Safely get the user ID if available
        user_id = getattr(request.state, "user_id", None)

        # Sanitize headers (remove sensitive information)
        headers = self._sanitize_headers(dict(request.headers))

        # Log the incoming request
        event_details = {
            "http_method": method,
            "path": path,
            "query_params": query_params,
            "headers": headers,
        }

        log_security_event(
            event_type="HTTP_REQUEST",
            message=f"{method} {path}",
            level=SECURITY_AUDIT,
            user_id=user_id,
            request=request,
            details=event_details,
        )

        # Process the request
        response = await call_next(request)

        # Calculate request duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Log the response
        response_details = {
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        }

        # Determine event type based on status code
        if 400 <= response.status_code < 500:
            event_type = "CLIENT_ERROR"
            message = f"{method} {path} resulted in client error {response.status_code}"
        elif response.status_code >= 500:
            event_type = "SERVER_ERROR"
            message = f"{method} {path} resulted in server error {response.status_code}"
        else:
            event_type = "HTTP_RESPONSE"
            message = f"{method} {path} completed with status {response.status_code}"

        log_security_event(
            event_type=event_type,
            message=message,
            level=SECURITY_AUDIT,
            user_id=user_id,
            request=request,
            details=response_details,
        )

        return response

    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Remove sensitive information from headers."""
        sanitized = {}
        for key, value in headers.items():
            if key.lower() in self.sensitive_headers:
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        return sanitized
