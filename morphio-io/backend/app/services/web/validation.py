import ipaddress
import logging
import re
import socket

logger = logging.getLogger(__name__)


def is_private_or_local_address(url: str) -> bool:
    """
    Check if URL resolves to a private/local/reserved IP.

    :param url: The URL to check
    :return: True if the URL resolves to a private, local, or reserved IP address; False otherwise
    """
    try:
        pattern = r"^(?:http[s]?://)?([^:/]+)"
        match = re.match(pattern, url.lower())
        if not match:
            return True
        hostname = match.group(1)
        ip = socket.gethostbyname(hostname)
        ip_addr = ipaddress.ip_address(ip)
        return (
            ip_addr.is_loopback
            or ip_addr.is_private
            or ip_addr.is_link_local
            or ip_addr.is_reserved
            or ip_addr.is_multicast
        )
    except Exception:
        return True
