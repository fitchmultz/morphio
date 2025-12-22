"""
Unit tests for the diarization schema and services.
"""

from app.schemas.diarization_schema import (
    DiarizationResult,
    SpeakerSegment,
    SpeakerUtterance,
    TranscriptionSpeakerSegment,
    WordTiming,
)


class TestWordTiming:
    """Tests for WordTiming schema."""

    def test_create_word_timing(self):
        """Test basic word timing creation."""
        word = WordTiming(
            word="hello",
            start_time=0.0,
            end_time=0.5,
            confidence=0.95,
        )
        assert word.word == "hello"
        assert word.start_time == 0.0
        assert word.end_time == 0.5
        assert word.confidence == 0.95

    def test_word_timing_optional_confidence(self):
        """Test word timing without confidence."""
        word = WordTiming(
            word="world",
            start_time=0.5,
            end_time=1.0,
        )
        assert word.word == "world"
        assert word.confidence is None


class TestSpeakerSegment:
    """Tests for SpeakerSegment schema."""

    def test_create_speaker_segment(self):
        """Test basic speaker segment creation."""
        segment = SpeakerSegment(
            speaker_id="SPEAKER_00",
            start_time=0.0,
            end_time=5.0,
            confidence=0.87,
        )
        assert segment.speaker_id == "SPEAKER_00"
        assert segment.start_time == 0.0
        assert segment.end_time == 5.0
        assert segment.confidence == 0.87

    def test_speaker_segment_optional_confidence(self):
        """Test speaker segment without confidence."""
        segment = SpeakerSegment(
            speaker_id="SPEAKER_01",
            start_time=5.0,
            end_time=10.0,
        )
        assert segment.speaker_id == "SPEAKER_01"
        assert segment.confidence is None


class TestSpeakerUtterance:
    """Tests for SpeakerUtterance schema."""

    def test_create_speaker_utterance(self):
        """Test speaker utterance creation."""
        words = [
            WordTiming(word="hello", start_time=0.0, end_time=0.3),
            WordTiming(word="world", start_time=0.4, end_time=0.7),
        ]
        utterance = SpeakerUtterance(
            speaker_id="SPEAKER_00",
            text="hello world",
            start_time=0.0,
            end_time=0.7,
            words=words,
        )
        assert utterance.speaker_id == "SPEAKER_00"
        assert utterance.text == "hello world"
        assert len(utterance.words) == 2

    def test_speaker_utterance_empty_words(self):
        """Test speaker utterance with empty words list."""
        utterance = SpeakerUtterance(
            speaker_id="SPEAKER_00",
            text="hello world",
            start_time=0.0,
            end_time=0.7,
        )
        assert utterance.words == []


class TestDiarizationResult:
    """Tests for DiarizationResult schema."""

    def test_create_diarization_result(self):
        """Test diarization result creation."""
        segments = [
            SpeakerSegment(speaker_id="SPEAKER_00", start_time=0.0, end_time=5.0),
            SpeakerSegment(speaker_id="SPEAKER_01", start_time=5.5, end_time=10.0),
        ]
        result = DiarizationResult(
            segments=segments,
            num_speakers=2,
            processing_time_seconds=3.5,
            model_name="pyannote/speaker-diarization-3.1",
        )
        assert len(result.segments) == 2
        assert result.num_speakers == 2
        assert result.processing_time_seconds == 3.5
        assert result.model_name == "pyannote/speaker-diarization-3.1"

    def test_diarization_result_defaults(self):
        """Test diarization result with defaults."""
        result = DiarizationResult()
        assert result.segments == []
        assert result.num_speakers == 0
        assert result.processing_time_seconds == 0.0
        assert result.model_name == "pyannote/speaker-diarization-3.1"


class TestTranscriptionSpeakerSegment:
    """Tests for TranscriptionSpeakerSegment schema."""

    def test_create_transcription_speaker_segment(self):
        """Test transcription speaker segment creation."""
        segment = TranscriptionSpeakerSegment(
            speaker_id="SPEAKER_00",
            start_time=0.0,
            end_time=3.0,
            text="Hello, how are you?",
        )
        assert segment.speaker_id == "SPEAKER_00"
        assert segment.start_time == 0.0
        assert segment.end_time == 3.0
        assert segment.text == "Hello, how are you?"
