"""
Unified FFmpeg utilities for audio and video processing.
"""

import asyncio
import shutil
from dataclasses import dataclass
from pathlib import Path

from morphio_core.exceptions import FFmpegError


@dataclass(frozen=True)
class FFmpegConfig:
    """Configuration for FFmpeg binary paths.

    Allows specifying custom paths to FFmpeg and ffprobe binaries,
    useful for containerized environments, non-standard installations,
    or when multiple FFmpeg versions are available.

    Args:
        ffmpeg_path: Path to ffmpeg binary (auto-detected if None)
        ffprobe_path: Path to ffprobe binary (auto-detected if None)

    Example:
        # Auto-detect (default)
        config = FFmpegConfig()

        # Custom paths
        config = FFmpegConfig(
            ffmpeg_path="/opt/ffmpeg/bin/ffmpeg",
            ffprobe_path="/opt/ffmpeg/bin/ffprobe",
        )

        # Use in functions
        duration = await probe_duration(path, config=config)
    """

    ffmpeg_path: str | None = None
    ffprobe_path: str | None = None

    def get_ffmpeg(self) -> str:
        """Get FFmpeg path, using auto-detection if not configured."""
        if self.ffmpeg_path:
            return self.ffmpeg_path
        found = shutil.which("ffmpeg")
        if not found:
            raise FFmpegError(
                message="FFmpeg not found. Install FFmpeg or configure ffmpeg_path.",
                command=["ffmpeg"],
            )
        return found

    def get_ffprobe(self) -> str:
        """Get ffprobe path, using auto-detection if not configured."""
        if self.ffprobe_path:
            return self.ffprobe_path
        found = shutil.which("ffprobe")
        if not found:
            raise FFmpegError(
                message="ffprobe not found. Install FFmpeg or configure ffprobe_path.",
                command=["ffprobe"],
            )
        return found


# Default config for module-level convenience
_default_config = FFmpegConfig()


def ensure_ffmpeg_available(config: FFmpegConfig | None = None) -> None:
    """
    Check that FFmpeg and ffprobe are installed and available.

    Args:
        config: Optional FFmpegConfig with custom binary paths

    Raises:
        FFmpegError: If FFmpeg or ffprobe is not found
    """
    cfg = config or _default_config
    # These will raise FFmpegError if not found
    cfg.get_ffmpeg()
    cfg.get_ffprobe()


async def run_ffmpeg(
    args: list[str],
    *,
    timeout: float | None = None,
    config: FFmpegConfig | None = None,
) -> tuple[bytes, bytes]:
    """
    Run FFmpeg command asynchronously.

    Args:
        args: FFmpeg arguments (without 'ffmpeg' prefix)
        timeout: Optional timeout in seconds
        config: Optional FFmpegConfig with custom binary paths

    Returns:
        Tuple of (stdout, stderr)

    Raises:
        FFmpegError: If command fails
    """
    cfg = config or _default_config
    ffmpeg_bin = cfg.get_ffmpeg()
    cmd = [ffmpeg_bin, "-y"] + args  # -y to overwrite without asking

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout,
        )
    except TimeoutError as e:
        process.kill()
        raise FFmpegError(
            message="FFmpeg command timed out",
            command=cmd,
        ) from e

    if process.returncode != 0:
        raise FFmpegError(
            message=f"FFmpeg exited with code {process.returncode}",
            command=cmd,
            stderr=stderr.decode(errors="replace"),
        )

    return stdout, stderr


async def probe_duration(
    path: Path,
    *,
    config: FFmpegConfig | None = None,
) -> float:
    """
    Get duration of media file in seconds using ffprobe.

    Args:
        path: Path to media file
        config: Optional FFmpegConfig with custom binary paths

    Returns:
        Duration in seconds

    Raises:
        FFmpegError: If probe fails
    """
    cfg = config or _default_config
    ffprobe_bin = cfg.get_ffprobe()
    cmd = [
        ffprobe_bin,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise FFmpegError(
            message="ffprobe failed",
            command=cmd,
            stderr=stderr.decode(errors="replace"),
        )

    try:
        return float(stdout.decode().strip())
    except ValueError as e:
        raise FFmpegError(
            message="Could not parse duration from ffprobe output",
            command=cmd,
            stderr=stdout.decode(errors="replace"),
        ) from e


async def convert_to_audio(
    input_path: Path,
    output_path: Path,
    *,
    audio_codec: str = "libmp3lame",
    audio_bitrate: str = "192k",
    config: FFmpegConfig | None = None,
) -> None:
    """
    Extract/convert audio from video file.

    Args:
        input_path: Source video/audio file
        output_path: Destination audio file
        audio_codec: Audio codec (default: libmp3lame for MP3)
        audio_bitrate: Audio bitrate (default: 192k)
        config: Optional FFmpegConfig with custom binary paths

    Raises:
        FFmpegError: If conversion fails
    """
    await run_ffmpeg(
        [
            "-i",
            str(input_path),
            "-vn",  # No video
            "-acodec",
            audio_codec,
            "-ab",
            audio_bitrate,
            str(output_path),
        ],
        config=config,
    )
