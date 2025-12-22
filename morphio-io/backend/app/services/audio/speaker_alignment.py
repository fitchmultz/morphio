"""
Speaker-to-text alignment service.

Re-exports from app/adapters/speaker_alignment.py which wraps morphio-core.
This module maintains backward compatibility with existing imports.
"""

from ...adapters.speaker_alignment import (
    align_speakers_to_words,
    find_overlapping_speaker,
    format_diarized_transcript,
    merge_cross_chunk_speakers,
    utterances_to_segments,
)

__all__ = [
    "align_speakers_to_words",
    "find_overlapping_speaker",
    "format_diarized_transcript",
    "merge_cross_chunk_speakers",
    "utterances_to_segments",
]
