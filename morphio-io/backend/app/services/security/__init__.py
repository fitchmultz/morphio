"""Security services package."""

# Authentication
from .authentication import (
    get_current_user,
    get_optional_current_user,
    get_password_hash,
    is_password_complex,
    verify_password,
)

# Authorization
from .authorization import (
    Permission,
    check_permission,
    check_resource_owner,
    get_user_permissions,
)

# Protection
from .protection import (
    rate_limit_by_ip,
    sanitize_input,
    track_login_attempts,
    validate_headers,
)

# Token management
from .tokens import (
    create_access_token,
    create_refresh_token,
    create_token,
    verify_token,
)

# Cookie management
from .cookies import (
    clear_auth_cookies,
    clear_refresh_cookie,
    set_csrf_cookie,
    set_refresh_cookie,
)

__all__ = [
    # Authentication
    "verify_password",
    "get_password_hash",
    "is_password_complex",
    "get_current_user",
    "get_optional_current_user",
    # Token management
    "create_access_token",
    "create_refresh_token",
    "create_token",
    "verify_token",
    # Authorization
    "Permission",
    "check_permission",
    "check_resource_owner",
    "get_user_permissions",
    # Protection
    "rate_limit_by_ip",
    "sanitize_input",
    "track_login_attempts",
    "validate_headers",
    # Cookie management
    "set_refresh_cookie",
    "set_csrf_cookie",
    "clear_auth_cookies",
    "clear_refresh_cookie",
]
