"""Video downloading via yt-dlp."""

import asyncio
from pathlib import Path
from typing import Any

from ..exceptions import DownloadError, UnsupportedURLError
from .types import DownloadConfig, DownloadResult, OutputMode
from .url_utils import is_supported_url


async def download_video_audio(
    url: str,
    output_dir: str | Path,
    *,
    config: DownloadConfig | None = None,
    prefix: str | None = None,
) -> DownloadResult:
    """Download audio from a video URL using yt-dlp.

    Supports YouTube, Rumble, Twitter/X, and TikTok.

    Args:
        url: Video URL to download
        output_dir: Directory to save downloaded file
        config: Optional download configuration
        prefix: Optional prefix for output filename

    Returns:
        DownloadResult with path and metadata

    Raises:
        UnsupportedURLError: If URL is not from a supported platform
        DownloadError: If download fails

    Example:
        result = await download_video_audio(
            "https://youtube.com/watch?v=abc123",
            "/tmp/downloads",
        )
        print(f"Downloaded to: {result.output_path}")
    """
    if not is_supported_url(url):
        raise UnsupportedURLError(f"URL not supported: {url}")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cfg = config or DownloadConfig()

    # Build output template with optional prefix
    template = f"{prefix}_" + cfg.output_template if prefix else cfg.output_template
    outtmpl = str(output_dir / template)

    # Build yt-dlp options
    ydl_opts: dict[str, Any] = {
        "format": cfg.format_spec,
        "outtmpl": outtmpl,
        "noplaylist": cfg.no_playlist,
        "retries": cfg.retries,
        "concurrent_fragment_downloads": cfg.concurrent_fragments,
        "quiet": cfg.output_mode == OutputMode.QUIET,
        "no_warnings": cfg.output_mode == OutputMode.QUIET,
        "verbose": cfg.output_mode == OutputMode.VERBOSE,
        # YouTube-specific to reduce PO token issues
        "extractor_args": {"youtube": {"player_client": [cfg.youtube_player_client]}},
    }

    def do_download() -> tuple[str, dict[str, Any]]:
        """Run download in thread (yt-dlp is synchronous)."""
        try:
            import yt_dlp  # type: ignore[import-not-found]
        except ImportError as e:
            raise DownloadError("yt-dlp package not installed") from e

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return filename, info

    try:
        output_path, info = await asyncio.to_thread(do_download)

        return DownloadResult(
            output_path=Path(output_path),
            title=info.get("title"),
            duration=info.get("duration"),
            format=info.get("format"),
        )
    except DownloadError:
        raise
    except Exception as e:
        raise DownloadError(f"Download failed: {e}") from e


def has_ytdlp() -> bool:
    """Check if yt-dlp is installed.

    Returns:
        True if yt-dlp is available

    Example:
        if has_ytdlp():
            result = await download_video_audio(url, output_dir)
    """
    try:
        import yt_dlp  # type: ignore[import-not-found]  # noqa: F401

        return True
    except ImportError:
        return False
