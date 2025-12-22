"""
Video conversion utilities - re-exports from morphio-core adapter.

This module maintains backward compatibility with existing imports.
"""

from ...adapters.media import (
    convert_video_to_audio_ffmpeg,
    run_ffmpeg_command,
)

__all__ = [
    "convert_video_to_audio_ffmpeg",
    "run_ffmpeg_command",
]
