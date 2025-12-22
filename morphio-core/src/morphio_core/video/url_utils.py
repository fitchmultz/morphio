"""URL validation and parsing utilities for video platforms."""

import re
from urllib.parse import urlparse

from .types import VideoPlatform

# Platform URL patterns
PLATFORM_PATTERNS: dict[VideoPlatform, re.Pattern[str]] = {
    "youtube": re.compile(
        r"(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/",
        re.IGNORECASE,
    ),
    "rumble": re.compile(
        r"(?:https?://)?(?:www\.)?rumble\.com/",
        re.IGNORECASE,
    ),
    "twitter": re.compile(
        r"(?:https?://)?(?:www\.)?(?:x\.com|twitter\.com)/",
        re.IGNORECASE,
    ),
    "tiktok": re.compile(
        r"(?:https?://)?(?:www\.)?(?:tiktok\.com|vm\.tiktok\.com)/",
        re.IGNORECASE,
    ),
}

# YouTube video ID extraction patterns
YOUTUBE_ID_PATTERNS = [
    re.compile(r"(?:v=|/)([0-9A-Za-z_-]{11})(?:[^\s]*)?"),
    re.compile(r"youtu\.be/([0-9A-Za-z_-]{11})(?:[^\s]*)?"),
    re.compile(r"youtube\.com/shorts/([0-9A-Za-z_-]{11})(?:[^\s]*)?"),
    re.compile(r"youtube\.com/live/([0-9A-Za-z_-]{11})(?:[^\s]*)?"),
]


def detect_platform(url: str) -> VideoPlatform:
    """Detect which video platform a URL belongs to.

    Args:
        url: Video URL to analyze

    Returns:
        Platform identifier or "unknown"

    Example:
        >>> detect_platform("https://youtube.com/watch?v=abc123")
        'youtube'
        >>> detect_platform("https://example.com")
        'unknown'
    """
    url = url.strip()
    for platform, pattern in PLATFORM_PATTERNS.items():
        if pattern.search(url):
            return platform
    return "unknown"


def is_supported_url(url: str) -> bool:
    """Check if URL is from a supported video platform.

    Args:
        url: URL to check

    Returns:
        True if URL is from a supported platform

    Example:
        >>> is_supported_url("https://youtube.com/watch?v=abc123")
        True
        >>> is_supported_url("https://example.com/video.mp4")
        False
    """
    return detect_platform(url) != "unknown"


def extract_youtube_id(url: str) -> str | None:
    """Extract YouTube video ID from a URL.

    Handles various YouTube URL formats:
    - youtube.com/watch?v=VIDEO_ID
    - youtu.be/VIDEO_ID
    - youtube.com/shorts/VIDEO_ID
    - youtube.com/live/VIDEO_ID

    Args:
        url: YouTube URL

    Returns:
        11-character video ID or None if not found

    Example:
        >>> extract_youtube_id("https://youtube.com/watch?v=dQw4w9WgXcQ")
        'dQw4w9WgXcQ'
        >>> extract_youtube_id("https://youtu.be/dQw4w9WgXcQ")
        'dQw4w9WgXcQ'
    """
    # Clean up malformed URLs (sometimes pasted incorrectly)
    cleaned = url.strip()
    cleaned = cleaned.replace("https://youtube.com/watch?v=https://", "https://")
    cleaned = cleaned.replace("https://youtube.com/watch?v=http://", "http://")
    cleaned = cleaned.replace("youtube.com/watch?v=www.", "www.")

    for pattern in YOUTUBE_ID_PATTERNS:
        match = pattern.search(cleaned)
        if match:
            return match.group(1)
    return None


def is_youtube_url(url: str) -> bool:
    """Check if URL is a YouTube URL.

    Args:
        url: URL to check

    Returns:
        True if URL is from YouTube

    Example:
        >>> is_youtube_url("https://youtube.com/watch?v=abc123")
        True
        >>> is_youtube_url("https://vimeo.com/123456")
        False
    """
    return detect_platform(url) == "youtube"


def is_valid_url(url: str) -> bool:
    """Check if string is a valid URL with scheme and netloc.

    Args:
        url: String to validate

    Returns:
        True if valid URL

    Example:
        >>> is_valid_url("https://example.com/video.mp4")
        True
        >>> is_valid_url("/path/to/file.mp4")
        False
    """
    if not url:
        return False
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except ValueError:
        return False


def normalize_url(url: str) -> str:
    """Normalize a video URL.

    Adds https:// scheme if missing.

    Args:
        url: URL to normalize

    Returns:
        Normalized URL with scheme

    Example:
        >>> normalize_url("youtube.com/watch?v=abc123")
        'https://youtube.com/watch?v=abc123'
        >>> normalize_url("https://youtube.com/watch?v=abc123")
        'https://youtube.com/watch?v=abc123'
    """
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url
