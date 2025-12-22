"""
Unified FFmpeg utilities for audio and video processing.
"""

import asyncio
import shutil
from pathlib import Path

from morphio_core.exceptions import FFmpegError


def ensure_ffmpeg_available() -> None:
    """
    Check that FFmpeg and ffprobe are installed and available.

    Raises:
        FFmpegError: If FFmpeg or ffprobe is not found
    """
    if not shutil.which("ffmpeg"):
        raise FFmpegError(
            message="FFmpeg not found. Please install FFmpeg.",
            command=["ffmpeg"],
        )
    if not shutil.which("ffprobe"):
        raise FFmpegError(
            message="ffprobe not found. Please install FFmpeg (includes ffprobe).",
            command=["ffprobe"],
        )


async def run_ffmpeg(
    args: list[str],
    *,
    timeout: float | None = None,
) -> tuple[bytes, bytes]:
    """
    Run FFmpeg command asynchronously.

    Args:
        args: FFmpeg arguments (without 'ffmpeg' prefix)
        timeout: Optional timeout in seconds

    Returns:
        Tuple of (stdout, stderr)

    Raises:
        FFmpegError: If command fails
    """
    cmd = ["ffmpeg", "-y"] + args  # -y to overwrite without asking

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


async def probe_duration(path: Path) -> float:
    """
    Get duration of media file in seconds using ffprobe.

    Args:
        path: Path to media file

    Returns:
        Duration in seconds

    Raises:
        FFmpegError: If probe fails
    """
    cmd = [
        "ffprobe",
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
) -> None:
    """
    Extract/convert audio from video file.

    Args:
        input_path: Source video/audio file
        output_path: Destination audio file
        audio_codec: Audio codec (default: libmp3lame for MP3)
        audio_bitrate: Audio bitrate (default: 192k)

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
        ]
    )
