"""
Shared test fixtures for morphio-core.
"""

import pytest


@pytest.fixture
def fake_dns_resolver():
    """
    Fixture that returns a fake DNS resolver for testing URL validation.

    Usage:
        def test_url_blocked(fake_dns_resolver):
            resolver = fake_dns_resolver({"example.com": ["93.184.216.34"]})
            validator = URLValidator(resolve_func=resolver)
            assert not validator.is_blocked("https://example.com")
    """

    def _create_resolver(hostname_to_ips: dict[str, list[str]]):
        def resolver(hostname: str, port: int, family: int, socktype: int):
            ips = hostname_to_ips.get(hostname, [])
            if not ips:
                import socket

                raise socket.gaierror(8, "Name or service not known")

            # Return in getaddrinfo format: (family, type, proto, canonname, sockaddr)
            import socket

            results = []
            for ip in ips:
                if ":" in ip:  # IPv6
                    results.append((socket.AF_INET6, socket.SOCK_STREAM, 0, "", (ip, port, 0, 0)))
                else:  # IPv4
                    results.append((socket.AF_INET, socket.SOCK_STREAM, 0, "", (ip, port)))
            return results

        return resolver

    return _create_resolver


@pytest.fixture
def sample_audio_path(tmp_path):
    """
    Fixture that creates a dummy audio file path for testing.

    Note: This doesn't create actual audio content - use for path-based tests only.
    """
    audio_file = tmp_path / "test_audio.mp3"
    audio_file.touch()
    return audio_file


@pytest.fixture
def sample_video_path(tmp_path):
    """
    Fixture that creates a dummy video file path for testing.

    Note: This doesn't create actual video content - use for path-based tests only.
    """
    video_file = tmp_path / "test_video.mp4"
    video_file.touch()
    return video_file
