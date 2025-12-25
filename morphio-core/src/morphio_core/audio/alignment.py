"""Speaker alignment - delegates to Rust implementation.

NOTE: Rust functions use #[derive(FromPyObject)] Input types, which means they
accept ANY Python object with matching attribute names. We can pass morphio-core
types directly - no need to create intermediate native objects.
"""

from morphio_native import SpeakerUtterance as NativeSpeakerUtterance
from morphio_native import TranscriptionSpeakerSegment as NativeTranscriptionSpeakerSegment
from morphio_native import align_speakers_to_words as _native_align
from morphio_native import find_overlapping_speaker as _native_find_overlapping
from morphio_native import format_diarized_transcript as _native_format
from morphio_native import merge_cross_chunk_speakers as _native_merge
from morphio_native import utterances_to_segments as _native_utterances_to_segments

from .types import (
    DiarizationResult,
    SpeakerSegment,
    SpeakerUtterance,
    TranscriptionSpeakerSegment,
    WordTiming,
)


def _from_native_utterance(u: NativeSpeakerUtterance) -> SpeakerUtterance:
    """Convert Rust output type to morphio-core type."""
    return SpeakerUtterance(
        speaker_id=u.speaker_id,
        text=u.text,
        start_time=u.start_time,
        end_time=u.end_time,
        words=[
            WordTiming(
                word=w.word,
                start_time=w.start_time,
                end_time=w.end_time,
                confidence=w.confidence,
            )
            for w in u.words
        ],
    )


def _from_native_segment(s: NativeTranscriptionSpeakerSegment) -> TranscriptionSpeakerSegment:
    """Convert Rust output type to morphio-core type."""
    return TranscriptionSpeakerSegment(
        speaker_id=s.speaker_id,
        start_time=s.start_time,
        end_time=s.end_time,
        text=s.text,
    )


def find_overlapping_speaker(
    word_start: float,
    word_end: float,
    segments: list[SpeakerSegment],
) -> str | None:
    """Find speaker with max overlap."""
    # Rust accepts any object with matching attributes via FromPyObject
    return _native_find_overlapping(word_start, word_end, segments)


def align_speakers_to_words(
    diarization: DiarizationResult,
    words: list[WordTiming],
) -> list[SpeakerUtterance]:
    """Align speakers to words using Rust interval tree."""
    # Pass morphio-core types directly - Rust extracts via FromPyObject
    native_result = _native_align(diarization.segments, words)
    return [_from_native_utterance(u) for u in native_result]


def merge_cross_chunk_speakers(
    chunk_utterances: list[list[SpeakerUtterance]],
    chunk_offsets: list[float],
) -> tuple[list[TranscriptionSpeakerSegment], dict[str, str]]:
    """Merge speakers - RETURNS TUPLE (segments, mapping)."""
    # Pass morphio-core types directly - Rust extracts via FromPyObject
    native_segments, speaker_map = _native_merge(chunk_utterances, chunk_offsets)
    return [_from_native_segment(s) for s in native_segments], dict(speaker_map)


def format_diarized_transcript(segments: list[TranscriptionSpeakerSegment]) -> str:
    """Format segments into transcript."""
    # Pass morphio-core types directly - Rust extracts via FromPyObject
    return _native_format(segments)


def utterances_to_segments(
    utterances: list[SpeakerUtterance],
) -> list[TranscriptionSpeakerSegment]:
    """Convert utterances to segments."""
    # Pass morphio-core types directly - Rust extracts via FromPyObject
    native_segments = _native_utterances_to_segments(utterances)
    return [_from_native_segment(s) for s in native_segments]
