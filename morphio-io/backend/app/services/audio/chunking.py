"""
Audio file chunking - re-exports from morphio-core adapter.

This module maintains backward compatibility with existing imports.
The morphio-core implementation provides FFmpeg-based audio segmentation.
"""

from ...adapters.audio import (
    chunk_audio_file,
    cleanup_chunks,
    probe_audio_duration,
    segment_audio_fast,
    segment_audio_with_overlap,
)

__all__ = [
    "chunk_audio_file",
    "cleanup_chunks",
    "probe_audio_duration",
    "segment_audio_fast",
    "segment_audio_with_overlap",
]
