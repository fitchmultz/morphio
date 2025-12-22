"""
Video processing utilities.

Provides:
- YouTube URL parsing and validation
- Video downloading via yt-dlp
- Multi-platform support (YouTube, Rumble, Twitter, TikTok)
"""

from .download import download_video_audio, has_ytdlp
from .types import DownloadConfig, DownloadResult, VideoPlatform
from .url_utils import (
    detect_platform,
    extract_youtube_id,
    is_supported_url,
    is_valid_url,
    is_youtube_url,
    normalize_url,
)

__all__ = [
    # Types
    "DownloadConfig",
    "DownloadResult",
    "VideoPlatform",
    # URL utilities
    "detect_platform",
    "is_supported_url",
    "extract_youtube_id",
    "is_youtube_url",
    "is_valid_url",
    "normalize_url",
    # Download
    "download_video_audio",
    "has_ytdlp",
]
