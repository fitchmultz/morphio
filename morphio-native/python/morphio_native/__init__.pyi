"""Type stubs for morphio-native Rust extension."""

from typing import Any

class AnonymizationResult:
    text: str
    mapping: dict[str, str]
    reverse_mapping: dict[str, str]
    counters: dict[str, int]
    content_hash: str

    def __init__(
        self,
        text: str,
        mapping: dict[str, str],
        reverse_mapping: dict[str, str],
        counters: dict[str, int],
        content_hash: str,
    ) -> None: ...

def anonymize(content: str) -> AnonymizationResult: ...

class SpeakerSegment:
    speaker_id: str
    start_time: float
    end_time: float
    confidence: float | None

    def __init__(
        self,
        speaker_id: str,
        start_time: float,
        end_time: float,
        confidence: float | None = None,
    ) -> None: ...

class WordTiming:
    word: str
    start_time: float
    end_time: float
    confidence: float | None

    def __init__(
        self,
        word: str,
        start_time: float,
        end_time: float,
        confidence: float | None = None,
    ) -> None: ...

class SpeakerUtterance:
    speaker_id: str
    text: str
    start_time: float
    end_time: float
    words: list[WordTiming]

    def __init__(
        self,
        speaker_id: str,
        text: str,
        start_time: float,
        end_time: float,
        words: list[WordTiming],
    ) -> None: ...

class TranscriptionSpeakerSegment:
    speaker_id: str
    start_time: float
    end_time: float
    text: str

    def __init__(
        self,
        speaker_id: str,
        start_time: float,
        end_time: float,
        text: str,
    ) -> None: ...

def find_overlapping_speaker(
    word_start: float,
    word_end: float,
    segments: list[Any],  # Accepts any object with matching attributes
) -> str | None: ...

def align_speakers_to_words(
    segments: list[Any],  # Accepts any object with matching attributes
    words: list[Any],  # Accepts any object with matching attributes
) -> list[SpeakerUtterance]: ...

def merge_cross_chunk_speakers(
    chunk_utterances: list[list[Any]],  # Accepts any object with matching attributes
    chunk_offsets: list[float],
) -> tuple[list[TranscriptionSpeakerSegment], dict[str, str]]: ...

def format_diarized_transcript(
    segments: list[Any],  # Accepts any object with matching attributes
) -> str: ...

def utterances_to_segments(
    utterances: list[Any],  # Accepts any object with matching attributes
) -> list[TranscriptionSpeakerSegment]: ...
