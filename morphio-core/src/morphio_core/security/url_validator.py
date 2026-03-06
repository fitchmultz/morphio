"""
Proper SSRF protection that:
1. Parses URL with urllib.parse.urlsplit
2. Enforces allowed schemes (http/https only by default)
3. Resolves ALL A and AAAA records using socket.getaddrinfo
4. Checks EVERY resolved IP against blocked ranges
5. Treats resolution failures as blocked (safe failure mode)

IMPORTANT CAVEATS (document for callers):

1. REDIRECTS: This validator checks a single URL. If your HTTP client follows
   redirects, you MUST validate each redirect target URL before following it.
   Otherwise: first URL passes -> redirect lands on blocked IP.

   Solution: Use a redirect hook/callback to validate each Location header,
   or disable auto-redirects and validate manually.

2. DNS REBINDING: Validation at string time cannot fully prevent DNS rebinding
   if the HTTP client re-resolves the hostname later. Between validation and
   connection, a malicious DNS server could return a different (blocked) IP.

   Stronger defense: Resolve once, validate IPs, then connect directly to the
   validated IP while sending the original hostname in SNI/Host header. This
   requires cooperation from the HTTP client layer (e.g., custom resolver or
   connect override).

This validator provides the baseline defense. For high-security contexts,
combine with HTTP client-level controls.
"""

import ipaddress
import socket
from collections.abc import Callable
from urllib.parse import urlsplit

from morphio_core.exceptions import SSRFBlockedError
from morphio_core.security.types import URLValidatorConfig


class URLValidator:
    """URL safety validator with comprehensive SSRF protection."""

    def __init__(
        self,
        config: URLValidatorConfig | None = None,
        *,
        resolve_func: Callable[[str, int, int, int], list[tuple]] | None = None,
    ):
        """
        Initialize validator.

        Args:
            config: Validation configuration
            resolve_func: Optional DNS resolver for testing (default: socket.getaddrinfo)
        """
        self._config = config or URLValidatorConfig()
        self._resolve = resolve_func or socket.getaddrinfo
        self._blocked_networks = self._build_blocked_networks()
        self._allowed_networks = self._build_allowed_networks()

    def _build_blocked_networks(
        self,
    ) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
        """Build list of blocked IP networks."""
        networks = []

        # Add custom blocked CIDRs
        for cidr in self._config.custom_blocked_cidrs:
            networks.append(ipaddress.ip_network(cidr, strict=False))

        return networks

    def _build_allowed_networks(
        self,
    ) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
        """Build list of explicitly allowed IP networks (overrides blocks)."""
        networks = []
        for cidr in self._config.custom_allowed_cidrs:
            networks.append(ipaddress.ip_network(cidr, strict=False))
        return networks

    def _is_ip_blocked(self, ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        """Check if a single IP address should be blocked."""
        # Check explicit allows first (override blocks)
        for network in self._allowed_networks:
            if ip in network:
                return False

        # Check built-in categories
        if self._config.block_loopback and ip.is_loopback:
            return True
        if self._config.block_private and ip.is_private:
            return True
        if self._config.block_link_local and ip.is_link_local:
            return True
        if self._config.block_reserved and ip.is_reserved:
            return True
        if self._config.block_multicast and ip.is_multicast:
            return True

        # Check custom blocked CIDRs
        return any(ip in network for network in self._blocked_networks)

    def is_blocked(self, url: str) -> bool:
        """
        Check if URL should be blocked (SSRF protection).

        Resolves ALL A and AAAA records and checks each IP.
        Returns True if ANY resolved IP is blocked.
        """
        try:
            parsed = urlsplit(url)

            # Check scheme
            if parsed.scheme not in self._config.allowed_schemes:
                return True

            # Extract hostname
            hostname = parsed.hostname
            if not hostname:
                return True

            # Get port (default to 443 for https, 80 for http)
            port = parsed.port or (443 if parsed.scheme == "https" else 80)

            # Resolve ALL addresses (IPv4 and IPv6)
            try:
                # AF_UNSPEC gets both A and AAAA records
                addr_info = self._resolve(hostname, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
            except socket.gaierror, socket.herror, OSError:
                # DNS resolution failed - block by default (fail closed)
                return self._config.block_on_resolution_error

            if not addr_info:
                return self._config.block_on_resolution_error

            # Check EVERY resolved IP
            for _family, _, _, _, sockaddr in addr_info:
                ip_str = sockaddr[0]
                try:
                    ip = ipaddress.ip_address(ip_str)
                    if self._is_ip_blocked(ip):
                        return True
                except ValueError:
                    # Invalid IP - treat as blocked
                    return True

            return False

        except Exception:
            # Any parsing error - block by default
            return True

    def validate(self, url: str) -> None:
        """
        Validate URL and raise if blocked.

        Raises:
            SSRFBlockedError: If URL is blocked
        """
        if self.is_blocked(url):
            raise SSRFBlockedError(f"URL blocked by SSRF protection: {url}")
