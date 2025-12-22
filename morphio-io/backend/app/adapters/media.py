"""
Media adapter - wraps morphio-core FFmpeg utilities.

Translates FFmpegError exceptions to ApplicationException.
"""

from pathlib import Path

from morphio_core.exceptions import FFmpegError
from morphio_core.media.ffmpeg import (
    convert_to_audio,
    ensure_ffmpeg_available,
    probe_duration,
    run_ffmpeg,
)

from ..utils.error_handlers import ApplicationException


async def run_ffmpeg_command(args: list[str], *, timeout: float | None = None) -> None:
    """
    Run an FFmpeg command with the provided arguments.

    Args:
        args: FFmpeg arguments (without 'ffmpeg' prefix)
        timeout: Optional timeout in seconds

    Raises:
        ApplicationException: If FFmpeg command fails
    """
    try:
        await run_ffmpeg(args, timeout=timeout)
    except FFmpegError as e:
        raise ApplicationException(
            message=str(e),
            status_code=500,
        ) from e


async def convert_video_to_audio_ffmpeg(
    video_path: str,
    audio_path: str,
    *,
    audio_codec: str = "libmp3lame",
    audio_bitrate: str = "192k",
) -> None:
    """
    Convert a video file to audio using FFmpeg.

    Args:
        video_path: Source video file path
        audio_path: Destination audio file path
        audio_codec: Audio codec (default: libmp3lame for MP3)
        audio_bitrate: Audio bitrate (default: 192k)

    Raises:
        ApplicationException: If conversion fails
    """
    try:
        await convert_to_audio(
            Path(video_path),
            Path(audio_path),
            audio_codec=audio_codec,
            audio_bitrate=audio_bitrate,
        )
    except FFmpegError as e:
        raise ApplicationException(
            message=f"Error converting video to audio: {e}",
            status_code=500,
        ) from e


async def get_media_duration(path: str | Path) -> float:
    """
    Get duration of media file in seconds.

    Args:
        path: Path to media file

    Returns:
        Duration in seconds

    Raises:
        ApplicationException: If probe fails
    """
    try:
        return await probe_duration(Path(path))
    except FFmpegError as e:
        raise ApplicationException(
            message=f"Error getting media duration: {e}",
            status_code=500,
        ) from e


def check_ffmpeg_available() -> None:
    """
    Check that FFmpeg and ffprobe are available.

    Raises:
        ApplicationException: If FFmpeg is not installed
    """
    try:
        ensure_ffmpeg_available()
    except FFmpegError as e:
        raise ApplicationException(
            message=str(e),
            status_code=500,
        ) from e


__all__ = [
    "run_ffmpeg_command",
    "convert_video_to_audio_ffmpeg",
    "get_media_duration",
    "check_ffmpeg_available",
]
