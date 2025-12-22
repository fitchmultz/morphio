"""
URL validation for web scraping - re-exports from morphio-core adapter.

This module provides SSRF protection by checking if URLs resolve to
private/local/reserved IPs. Uses morphio-core's URLValidator which
resolves ALL DNS records and checks each IP.
"""

from ...adapters.url_validation import is_url_safe


def is_private_or_local_address(url: str) -> bool:
    """
    Check if URL resolves to a private/local/reserved IP.

    Uses morphio-core's URLValidator which resolves ALL DNS A/AAAA records
    and checks each IP against private, loopback, link-local, reserved,
    and multicast ranges.

    Args:
        url: The URL to check

    Returns:
        True if the URL resolves to a private/local/reserved IP, False if safe
    """
    # is_url_safe returns True if safe, we want True if blocked
    return not is_url_safe(url)
