"""Rust-native performance extensions for morphio."""

from morphio_native._native import (
    # Anonymizer
    AnonymizationResult,
    anonymize,
    # Alignment
    SpeakerSegment,
    SpeakerUtterance,
    TranscriptionSpeakerSegment,
    WordTiming,
    align_speakers_to_words,
    find_overlapping_speaker,
    format_diarized_transcript,
    merge_cross_chunk_speakers,
    utterances_to_segments,
)

__all__ = [
    "AnonymizationResult",
    "anonymize",
    "SpeakerSegment",
    "WordTiming",
    "SpeakerUtterance",
    "TranscriptionSpeakerSegment",
    "find_overlapping_speaker",
    "align_speakers_to_words",
    "merge_cross_chunk_speakers",
    "format_diarized_transcript",
    "utterances_to_segments",
]
