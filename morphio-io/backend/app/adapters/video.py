"""
Video utilities adapter - wraps morphio-core video module.

Provides video URL validation and downloading with exception translation.
"""

from morphio_core.exceptions import DownloadError, UnsupportedURLError
from morphio_core.video import (
    DownloadConfig,
    DownloadResult,
    detect_platform,
    download_video_audio,
    extract_youtube_id,
    has_ytdlp,
    is_supported_url,
    is_youtube_url,
    normalize_url,
)

from ..utils.error_handlers import ApplicationException


async def download_video_via_ytdlp(
    url: str,
    output_directory: str,
    *,
    job_id: str | None = None,
    video_id: str | None = None,
) -> str:
    """Download video audio using yt-dlp.

    This is a compatibility wrapper that matches the original
    morphio-io function signature.

    Args:
        url: Video URL to download
        output_directory: Directory for output file
        job_id: Optional job ID for filename prefix
        video_id: Optional video ID for filename prefix

    Returns:
        Path to downloaded file

    Raises:
        ApplicationException: On invalid URL (400) or download failure (500)
    """
    if not is_supported_url(url):
        raise ApplicationException("Invalid or unsupported video URL format", status_code=400)

    # Build prefix from video_id and job_id
    prefix = None
    if video_id or job_id:
        parts = [video_id or "vid"]
        if job_id:
            parts.append(job_id)
        prefix = "_".join(parts)

    try:
        result = await download_video_audio(
            url,
            output_directory,
            prefix=prefix,
        )
        return str(result.output_path)
    except UnsupportedURLError as e:
        raise ApplicationException(str(e), status_code=400)
    except DownloadError:
        raise ApplicationException("Unable to download video content.", status_code=500)


def get_yt_video_id(url: str) -> str | None:
    """Extract YouTube video ID from URL.

    Compatibility wrapper for original morphio-io function name.
    """
    return extract_youtube_id(url)


def is_supported_video_url(url: str) -> bool:
    """Check if URL is from a supported video platform.

    Compatibility wrapper for original morphio-io function name.
    """
    return is_supported_url(url)


# Re-export morphio-core utilities directly
__all__ = [
    # Compatibility wrappers
    "download_video_via_ytdlp",
    "get_yt_video_id",
    "is_supported_video_url",
    # Direct re-exports
    "detect_platform",
    "is_youtube_url",
    "normalize_url",
    "has_ytdlp",
    "DownloadConfig",
    "DownloadResult",
]
