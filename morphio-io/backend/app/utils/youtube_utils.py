"""
YouTube/video utilities - re-exports from morphio-core via adapters.

This module maintains backward compatibility with existing imports.
All functionality is now provided by morphio-core library.
"""

from ..adapters.video import (
    download_video_via_ytdlp,
    get_yt_video_id,
    is_supported_video_url,
)

__all__ = [
    "download_video_via_ytdlp",
    "get_yt_video_id",
    "is_supported_video_url",
]
