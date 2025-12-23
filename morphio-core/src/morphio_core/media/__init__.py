"""
Media processing utilities.

Provides unified FFmpeg operations for audio and video processing.
"""

from morphio_core.media.ffmpeg import (
    FFmpegConfig,
    convert_to_audio,
    ensure_ffmpeg_available,
    probe_duration,
    run_ffmpeg,
)

__all__ = [
    "FFmpegConfig",
    "ensure_ffmpeg_available",
    "run_ffmpeg",
    "probe_duration",
    "convert_to_audio",
]
