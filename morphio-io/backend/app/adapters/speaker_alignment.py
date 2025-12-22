"""
Speaker alignment adapter - wraps morphio-core alignment functions.

Converts between morphio-io schema types and morphio-core types.
"""

from typing import Dict, List, Optional, Tuple

from morphio_core.audio import alignment as core_alignment
from morphio_core.audio import types as core_types

from ..schemas.diarization_schema import (
    DiarizationResult,
    SpeakerSegment,
    SpeakerUtterance,
    TranscriptionSpeakerSegment,
    WordTiming,
)


def _to_core_word_timing(word: WordTiming) -> core_types.WordTiming:
    """Convert morphio-io WordTiming to morphio-core WordTiming."""
    return core_types.WordTiming(
        word=word.word,
        start_time=word.start_time,
        end_time=word.end_time,
        confidence=word.confidence,
    )


def _to_core_speaker_segment(segment: SpeakerSegment) -> core_types.SpeakerSegment:
    """Convert morphio-io SpeakerSegment to morphio-core SpeakerSegment."""
    return core_types.SpeakerSegment(
        speaker_id=segment.speaker_id,
        start_time=segment.start_time,
        end_time=segment.end_time,
        confidence=segment.confidence,
    )


def _to_core_diarization_result(diarization: DiarizationResult) -> core_types.DiarizationResult:
    """Convert morphio-io DiarizationResult to morphio-core DiarizationResult."""
    return core_types.DiarizationResult(
        segments=[_to_core_speaker_segment(s) for s in diarization.segments],
        num_speakers=diarization.num_speakers,
    )


def _from_core_speaker_utterance(utterance: core_types.SpeakerUtterance) -> SpeakerUtterance:
    """Convert morphio-core SpeakerUtterance to morphio-io SpeakerUtterance."""
    return SpeakerUtterance(
        speaker_id=utterance.speaker_id,
        text=utterance.text,
        start_time=utterance.start_time,
        end_time=utterance.end_time,
        words=[
            WordTiming(
                word=w.word,
                start_time=w.start_time,
                end_time=w.end_time,
                confidence=w.confidence,
            )
            for w in utterance.words
        ],
    )


def _from_core_transcription_speaker_segment(
    segment: core_types.TranscriptionSpeakerSegment,
) -> TranscriptionSpeakerSegment:
    """Convert morphio-core TranscriptionSpeakerSegment to morphio-io."""
    return TranscriptionSpeakerSegment(
        speaker_id=segment.speaker_id,
        start_time=segment.start_time,
        end_time=segment.end_time,
        text=segment.text,
    )


# Public API - matches original speaker_alignment.py interface


def find_overlapping_speaker(
    word_start: float,
    word_end: float,
    segments: List[SpeakerSegment],
) -> Optional[str]:
    """Find the speaker whose segment overlaps most with the given word timing."""
    core_segments = [_to_core_speaker_segment(s) for s in segments]
    return core_alignment.find_overlapping_speaker(word_start, word_end, core_segments)


def align_speakers_to_words(
    diarization: DiarizationResult,
    words: List[WordTiming],
) -> List[SpeakerUtterance]:
    """Align speaker segments with word timings to produce speaker utterances."""
    core_diarization = _to_core_diarization_result(diarization)
    core_words = [_to_core_word_timing(w) for w in words]

    core_utterances = core_alignment.align_speakers_to_words(core_diarization, core_words)

    return [_from_core_speaker_utterance(u) for u in core_utterances]


def merge_cross_chunk_speakers(
    chunk_utterances: List[List[SpeakerUtterance]],
    chunk_offsets: List[float],
) -> Tuple[List[TranscriptionSpeakerSegment], Dict[str, str]]:
    """Merge speaker utterances across chunks, handling speaker ID consistency."""
    # Convert to core types
    core_chunk_utterances = [
        [
            core_types.SpeakerUtterance(
                speaker_id=u.speaker_id,
                text=u.text,
                start_time=u.start_time,
                end_time=u.end_time,
                words=[_to_core_word_timing(w) for w in u.words],
            )
            for u in utterances
        ]
        for utterances in chunk_utterances
    ]

    core_segments, speaker_map = core_alignment.merge_cross_chunk_speakers(
        core_chunk_utterances, chunk_offsets
    )

    return [_from_core_transcription_speaker_segment(s) for s in core_segments], speaker_map


def format_diarized_transcript(segments: List[TranscriptionSpeakerSegment]) -> str:
    """Format speaker segments into a readable transcript with inline labels."""
    core_segments = [
        core_types.TranscriptionSpeakerSegment(
            speaker_id=s.speaker_id,
            start_time=s.start_time,
            end_time=s.end_time,
            text=s.text,
        )
        for s in segments
    ]
    return core_alignment.format_diarized_transcript(core_segments)


def utterances_to_segments(
    utterances: List[SpeakerUtterance],
) -> List[TranscriptionSpeakerSegment]:
    """Convert utterances to transcription speaker segments."""
    core_utterances = [
        core_types.SpeakerUtterance(
            speaker_id=u.speaker_id,
            text=u.text,
            start_time=u.start_time,
            end_time=u.end_time,
            words=[_to_core_word_timing(w) for w in u.words],
        )
        for u in utterances
    ]
    core_segments = core_alignment.utterances_to_segments(core_utterances)
    return [_from_core_transcription_speaker_segment(s) for s in core_segments]
