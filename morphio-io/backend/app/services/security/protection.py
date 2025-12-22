import logging
from datetime import UTC, datetime, timedelta
from typing import Dict

from fastapi import Request, status

from ...config import settings
from ...utils.error_handlers import ApplicationException
from ...utils.security_logger import (
    SECURITY_ALERT,
    SECURITY_AUDIT,
    SecurityEventType,
    log_security_event,
)

logger = logging.getLogger(__name__)

# Simple rate limiting
ip_request_count: Dict[str, int] = {}
ip_request_reset: Dict[str, datetime] = {}

# Login attempt tracking
login_attempts: Dict[str, int] = {}
login_attempt_reset: Dict[str, datetime] = {}


async def rate_limit_by_ip(request: Request, limit: int = 100, window: int = 60) -> bool:
    """
    Rate limit requests by IP address.

    :param request: The FastAPI request
    :param limit: Maximum number of requests in the time window
    :param window: Time window in seconds
    :return: True if under limit, raises exception otherwise
    """
    client_ip = getattr(request.client, "host", "unknown")

    # Reset count if window has expired
    now = datetime.now(UTC)
    if client_ip in ip_request_reset and now > ip_request_reset[client_ip]:
        ip_request_count[client_ip] = 0

    # Initialize or increment count
    if client_ip not in ip_request_count:
        ip_request_count[client_ip] = 1
        ip_request_reset[client_ip] = now + timedelta(seconds=window)
    else:
        ip_request_count[client_ip] += 1

    # Check if over limit
    if ip_request_count[client_ip] > limit:
        log_security_event(
            event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
            message=f"Rate limit exceeded for IP: {client_ip}",
            level=SECURITY_AUDIT,
            ip_address=client_ip,
            request=request,
            details={
                "request_count": ip_request_count[client_ip],
                "limit": limit,
                "window_seconds": window,
                "path": request.url.path,
                "method": request.method,
            },
        )
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise ApplicationException(
            message="Too many requests. Please try again later.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    return True


def track_login_attempts(
    username: str, success: bool, max_attempts: int = 5, lockout_time: int = 300
) -> bool:
    """
    Track failed login attempts and implement account lockout.

    :param username: The username attempting to login
    :param success: Whether the login was successful
    :param max_attempts: Maximum number of failed attempts before lockout
    :param lockout_time: Lockout time in seconds
    :return: True if account is not locked, raises exception otherwise
    """
    now = datetime.now(UTC)

    # Reset count if lockout period has expired
    if username in login_attempt_reset and now > login_attempt_reset[username]:
        login_attempts[username] = 0

    # Check if account is locked
    if username in login_attempts and login_attempts[username] >= max_attempts:
        remaining_time = (login_attempt_reset[username] - now).total_seconds()
        if remaining_time > 0:
            log_security_event(
                event_type=SecurityEventType.ACCOUNT_LOCKED,
                message=f"Login attempt on locked account: {username}",
                level=SECURITY_ALERT,
                details={
                    "username": username,
                    "remaining_lockout_seconds": int(remaining_time),
                },
            )
            logger.warning(f"Account locked for user: {username}")
            raise ApplicationException(
                message=f"Account temporarily locked. Try again in {int(remaining_time)} seconds.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

    # If login succeeded, reset counter
    if success:
        if username in login_attempts and login_attempts[username] > 0:
            log_security_event(
                event_type=SecurityEventType.LOGIN_SUCCESS,
                message=f"Successful login after {login_attempts[username]} failed attempts: {username}",
                level=SECURITY_AUDIT,
                details={
                    "username": username,
                    "previous_failed_attempts": login_attempts[username],
                },
            )
        login_attempts[username] = 0
        return True

    # Increment failed login counter
    if username not in login_attempts:
        login_attempts[username] = 1
    else:
        login_attempts[username] += 1

    # Log failed login attempt
    log_security_event(
        event_type=SecurityEventType.LOGIN_FAILURE,
        message=f"Failed login attempt for user: {username}",
        level=SECURITY_AUDIT,
        details={
            "username": username,
            "attempt_number": login_attempts[username],
            "max_attempts": max_attempts,
        },
    )

    # Set lockout time if max attempts reached
    if login_attempts[username] >= max_attempts:
        login_attempt_reset[username] = now + timedelta(seconds=lockout_time)
        log_security_event(
            event_type=SecurityEventType.ACCOUNT_LOCKED,
            message=f"Account locked after {max_attempts} failed login attempts: {username}",
            level=SECURITY_ALERT,
            details={
                "username": username,
                "lockout_duration_seconds": lockout_time,
                "lockout_until": (now + timedelta(seconds=lockout_time)).isoformat(),
            },
        )
        logger.warning(f"Account locked for user: {username}")
        raise ApplicationException(
            message=f"Account temporarily locked for {lockout_time} seconds after too many failed attempts.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    return True


def validate_headers(request: Request) -> bool:
    """
    Validate security headers in the request.

    :param request: The FastAPI request
    :return: True if valid, raises exception otherwise
    """
    # Check for common security headers (placeholder implementation)
    # Add validation based on your security requirements

    # Example: Check for missing or insecure headers
    if (
        bool(getattr(settings, "SECURITY_STRICT_TRANSPORT", False))
        and request.url.scheme != "https"
    ):
        # Only enforce in production
        if getattr(settings, "APP_ENV", "development") == "production":
            log_security_event(
                event_type="INSECURE_TRANSPORT",
                message="Insecure transport (HTTP) detected in production environment",
                level=SECURITY_ALERT,
                request=request,
                details={
                    "scheme": request.url.scheme,
                    "path": request.url.path,
                    "headers": dict(request.headers),
                },
            )
            logger.warning("Insecure transport detected")
            raise ApplicationException(
                message="Secure connection required",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    return True


def sanitize_input(input_data: str) -> str:
    """
    Sanitize user input to prevent injection attacks.

    :param input_data: The input string to sanitize
    :return: The sanitized string
    """
    # Check for potentially malicious patterns
    suspicious_patterns = [
        "javascript:",
        "<script>",
        "eval(",
        "document.cookie",
        "onload=",
        "onerror=",
        "1=1",
        "drop table",
        "delete from",
        "--",
        "/*",
        "*/",
        "@@",
    ]

    # Log suspicious input
    for pattern in suspicious_patterns:
        if pattern.lower() in input_data.lower():
            log_security_event(
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                message="Potentially malicious input detected",
                level=SECURITY_ALERT,
                details={
                    "suspicious_pattern": pattern,
                    "input_sample": input_data[:100] + ("..." if len(input_data) > 100 else ""),
                },
            )
            break

    # Simple sanitization (in a real app, use a proper library)
    sanitized = input_data.replace("<", "&lt;").replace(">", "&gt;")

    return sanitized
