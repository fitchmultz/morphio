"""
URL validation adapter - wraps morphio-core URLValidator.

Provides the same interface as the original morphio-io validation
while delegating to morphio-core under the hood.
"""

from morphio_core.exceptions import SSRFBlockedError
from morphio_core.security import URLValidator, URLValidatorConfig

from ..utils.error_handlers import ApplicationException

# Shared validator instance (configured once)
_validator: URLValidator | None = None


def _get_validator() -> URLValidator:
    """Get or create shared validator instance."""
    global _validator
    if _validator is None:
        _validator = URLValidator(URLValidatorConfig())
    return _validator


def is_url_safe(url: str) -> bool:
    """Check if URL is safe (not blocked by SSRF protection).

    Args:
        url: URL to validate

    Returns:
        True if URL is safe to fetch
    """
    return not _get_validator().is_blocked(url)


def validate_url(url: str) -> None:
    """Validate URL, raising ApplicationException if blocked.

    Args:
        url: URL to validate

    Raises:
        ApplicationException: If URL is blocked (400 status)
    """
    try:
        _get_validator().validate(url)
    except SSRFBlockedError as e:
        raise ApplicationException(str(e), status_code=400)


# Re-export for convenience
__all__ = ["is_url_safe", "validate_url", "URLValidator", "URLValidatorConfig"]
