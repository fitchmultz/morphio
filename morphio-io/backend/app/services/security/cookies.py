"""
Centralized cookie management for consistent auth cookie handling.
Ensures consistent path, secure, and samesite attributes across all auth operations.
"""

from starlette.responses import Response

from ...config import settings

# Common cookie settings for all auth cookies
COOKIE_PATH = "/"
COOKIE_SAMESITE = "strict"


def _get_secure() -> bool:
    """Determine if cookies should be secure based on environment."""
    return settings.APP_ENV == "production"


def set_refresh_cookie(response: Response, token: str) -> None:
    """
    Set the refresh token in a secure HTTP-only cookie.

    Args:
        response: The response object to set the cookie on
        token: The refresh token value
    """
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=_get_secure(),
        samesite=COOKIE_SAMESITE,
        path=COOKIE_PATH,
        max_age=60 * 60 * 24 * settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS,
    )


def set_csrf_cookie(response: Response, token: str) -> None:
    """
    Set the CSRF token in a cookie (readable by JavaScript).

    Args:
        response: The response object to set the cookie on
        token: The CSRF token value
    """
    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=False,  # Allow JavaScript to read this cookie
        secure=_get_secure(),
        samesite=COOKIE_SAMESITE,
        path=COOKIE_PATH,
        max_age=settings.CSRF_COOKIE_EXPIRE_SECONDS,
    )


def clear_auth_cookies(response: Response) -> None:
    """
    Clear all auth-related cookies (refresh token and CSRF token).

    Args:
        response: The response object to clear cookies from
    """
    response.delete_cookie(
        key="refresh_token",
        path=COOKIE_PATH,
        secure=_get_secure(),
        samesite=COOKIE_SAMESITE,
    )
    response.delete_cookie(
        key="csrf_token",
        path=COOKIE_PATH,
        secure=_get_secure(),
        samesite=COOKIE_SAMESITE,
    )


def clear_refresh_cookie(response: Response) -> None:
    """
    Clear only the refresh token cookie.

    Args:
        response: The response object to clear the cookie from
    """
    response.delete_cookie(
        key="refresh_token",
        path=COOKIE_PATH,
        secure=_get_secure(),
        samesite=COOKIE_SAMESITE,
    )
