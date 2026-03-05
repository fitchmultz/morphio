import inspect
import json
import logging
import os
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from functools import wraps
from collections.abc import Coroutine
from typing import Any, ParamSpec, TypeVar, Optional, Union, Dict

from fastapi import Request

from ..config import settings


def redact_token_id(token_id: str | None) -> str | None:
    """
    Redact a token ID for safe logging.
    Shows first 4 and last 4 characters only.

    Example: "abc123xyz789def" -> "abc1...9def"
    """
    if not token_id:
        return None
    if len(token_id) < 8:
        return "***"
    return f"{token_id[:4]}...{token_id[-4:]}"


# Flag to track if security logging has been initialized
_security_logging_initialized = False

# Configure a dedicated security logger
security_logger = logging.getLogger("security")

# Define security log levels
SECURITY_AUDIT = 25  # Between INFO (20) and WARNING (30)
SECURITY_ALERT = 35  # Between WARNING (30) and ERROR (40)

# Register custom log levels with the logging module
logging.addLevelName(SECURITY_AUDIT, "AUDIT")
logging.addLevelName(SECURITY_ALERT, "ALERT")


def setup_security_logging():
    """
    Initialize security logging configuration.
    This should be called once at application startup.
    Idempotent: subsequent calls are no-ops.
    """
    global _security_logging_initialized

    # Prevent duplicate handler registration on reloads/multiple calls
    if _security_logging_initialized:
        return

    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.getcwd(), "log_files")
    os.makedirs(log_dir, exist_ok=True)

    # Configure security logger
    security_logger.setLevel(logging.DEBUG)  # Set to DEBUG to capture all levels

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.getLevelName(settings.LOG_LEVEL))

    # Create file handler for security logs
    security_log_file = os.path.join(log_dir, "security.log")
    file_handler = logging.FileHandler(security_log_file)
    file_handler.setLevel(logging.DEBUG)  # Log all security events to file

    # Create a detailed formatter
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] [%(correlation_id)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add handlers to the logger
    security_logger.addHandler(console_handler)
    security_logger.addHandler(file_handler)

    # Set propagate to False to prevent duplicate logs
    security_logger.propagate = False

    _security_logging_initialized = True
    security_logger.info("Security logging initialized", extra={"correlation_id": "SYSTEM"})


def log_security_event(
    event_type: str,
    message: str,
    level: int = SECURITY_AUDIT,
    user_id: Optional[Union[int, str]] = None,
    request: Optional[Request] = None,
    correlation_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log a security event with standardized format.

    Args:
        event_type: Type of security event (e.g., "LOGIN_ATTEMPT", "PERMISSION_CHANGE")
        message: Human-readable description of the event
        level: Log level (use standard logging levels or SECURITY_AUDIT, SECURITY_ALERT)
        user_id: ID of the user who triggered the event (if available)
        request: FastAPI request object (if available)
        correlation_id: Correlation ID to track related events (if available)
        ip_address: IP address of the client (if available)
        details: Additional details about the event
    """
    if details is None:
        details = {}

    # Extract correlation ID from request if not provided
    if correlation_id is None and request and hasattr(request.state, "correlation_id"):
        correlation_id = request.state.correlation_id
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())

    # Extract IP address from request if not provided
    if ip_address is None and request:
        ip_address = request.client.host if request.client else None

    # Create standardized security event
    event = {
        "timestamp": datetime.now(UTC).isoformat(),
        "event_type": event_type,
        "correlation_id": correlation_id,
        "user_id": user_id,
        "ip_address": ip_address,
        "message": message,
        **details,
    }

    # Log event with appropriate level
    security_logger.log(level, json.dumps(event), extra={"correlation_id": correlation_id})


def _format_audit_message(message: str, context: Dict[str, Any]) -> str:
    """
    Format an audit message template with context values.
    Supports both simple placeholders {param} and dotted attribute access {param.attr}.
    """
    import re

    def replace_placeholder(match: re.Match) -> str:
        placeholder = match.group(1)
        parts = placeholder.split(".")
        value = context.get(parts[0])

        # Navigate through dotted attributes
        for part in parts[1:]:
            if value is None:
                return f"{{{placeholder}}}"
            value = getattr(value, part, None)

        if value is None:
            return f"{{{placeholder}}}"
        return str(value)

    try:
        return re.sub(r"\{([^}]+)\}", replace_placeholder, message)
    except Exception:
        return f"{message} (error formatting message)"


def audit(
    event_type: str,
    message: Optional[str] = None,
) -> Callable:
    """
    Decorator to audit security-relevant function calls.

    Args:
        event_type: Type of security event
        message: Message template (can include {parameter_name} or {param.attr} for parameters)

    Example:
        @audit("USER_PERMISSION_CHANGE", "User {user_id} permissions changed to {new_role}")
        async def change_user_role(user_id: int, new_role: str, db: AsyncSession):
            ...

        @audit("LOGIN_ATTEMPT", "Login attempt for user: {user_login.email}")
        async def login(request: Request, user_login: UserLogin, db: AsyncSession):
            ...
    """

    P = ParamSpec("P")
    R = TypeVar("R")

    def decorator(
        func: Callable[P, Coroutine[Any, Any, R]],
    ) -> Callable[P, Coroutine[Any, Any, R]]:
        func_name = getattr(func, "__name__", str(func))
        sig = inspect.signature(func)

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start_time = time.time()
            result: R | None = None
            error = None

            # Bind args and kwargs to the function signature to get a mapping of all arguments
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            context: Dict[str, Any] = dict(bound_args.arguments)

            # Extract request from the arguments (usually named 'request')
            request: Request | None = context.get("request")
            # Fallback to find the request object if it has a different name
            if not isinstance(request, Request):
                request = next((arg for arg in context.values() if isinstance(arg, Request)), None)

            user_id: int | str | None = None
            raw_user_id = context.get("user_id")
            if isinstance(raw_user_id, (int, str)):
                user_id = raw_user_id
            elif raw_user_id is None and request:
                state_user_id = getattr(request.state, "user_id", None)
                if isinstance(state_user_id, (int, str)):
                    user_id = state_user_id

            try:
                # Execute the async function
                result = await func(*args, **kwargs)

                # Format message with actual parameter values
                formatted_message = message
                if message:
                    if result is not None and isinstance(result, dict):
                        for key, value in result.items():
                            if isinstance(key, str):
                                context[key] = value
                    formatted_message = _format_audit_message(message, context)

                # Log successful execution
                log_security_event(
                    event_type=event_type,
                    message=formatted_message or f"{func_name} executed successfully",
                    level=SECURITY_AUDIT,
                    user_id=user_id,
                    request=request,
                    details={
                        "function": func_name,
                        "duration_ms": int((time.time() - start_time) * 1000),
                        "success": True,
                    },
                )
                return result

            except Exception as e:
                error = str(e)
                # Log failure
                log_security_event(
                    event_type=f"{event_type}_ERROR",
                    message=f"Error in {func_name}: {error}",
                    level=SECURITY_ALERT,
                    user_id=user_id,
                    request=request,
                    details={
                        "function": func_name,
                        "duration_ms": int((time.time() - start_time) * 1000),
                        "success": False,
                        "error": error,
                    },
                )
                raise

        return wrapper

    return decorator


# Common security event types
class SecurityEventType:
    # Authentication events
    LOGIN_ATTEMPT = "LOGIN_ATTEMPT"
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILURE = "LOGIN_FAILURE"
    LOGOUT = "LOGOUT"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"
    PASSWORD_RESET_REQUEST = "PASSWORD_RESET_REQUEST"
    PASSWORD_RESET_COMPLETE = "PASSWORD_RESET_COMPLETE"

    # Authorization events
    ACCESS_DENIED = "ACCESS_DENIED"
    PERMISSION_CHANGE = "PERMISSION_CHANGE"
    ROLE_CHANGE = "ROLE_CHANGE"

    # User management
    USER_CREATED = "USER_CREATED"
    USER_DELETED = "USER_DELETED"
    USER_PROFILE_CHANGE = "USER_PROFILE_CHANGE"

    # Data access and modification
    SENSITIVE_DATA_ACCESS = "SENSITIVE_DATA_ACCESS"
    DATA_EXPORT = "DATA_EXPORT"
    CONTENT_CREATED = "CONTENT_CREATED"
    CONTENT_MODIFIED = "CONTENT_MODIFIED"
    CONTENT_DELETED = "CONTENT_DELETED"

    # System events
    CONFIG_CHANGE = "CONFIG_CHANGE"
    API_KEY_GENERATED = "API_KEY_GENERATED"
    API_KEY_REVOKED = "API_KEY_REVOKED"

    # Security-specific events
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
