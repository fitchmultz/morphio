"""Tests for audio processing module."""

import pytest

from morphio_core.audio import (
    AudioChunk,
    ChunkingConfig,
    DiarizationResult,
    SpeakerSegment,
    SpeakerUtterance,
    TranscriptionConfig,
    TranscriptionResult,
    TranscriptionSegment,
    TranscriptionSpeakerSegment,
    WordTiming,
    align_speakers_to_words,
    default_chunk_namer,
    format_diarized_transcript,
    has_faster_whisper,
    has_mlx_whisper,
    is_apple_silicon,
    merge_cross_chunk_speakers,
    utterances_to_segments,
)
from morphio_core.exceptions import BackendNotAvailableError, TranscriptionError


class TestAudioChunk:
    """Tests for AudioChunk model."""

    def test_audio_chunk_creation(self, tmp_path):
        """Test creating an AudioChunk."""
        chunk_path = tmp_path / "test.mp3"
        chunk = AudioChunk(chunk_path=chunk_path, start_time=0.0, end_time=10.0)

        assert chunk.chunk_path == chunk_path
        assert chunk.start_time == 0.0
        assert chunk.end_time == 10.0

    def test_audio_chunk_duration_computed(self, tmp_path):
        """Test that duration is computed correctly."""
        chunk = AudioChunk(chunk_path=tmp_path / "test.mp3", start_time=5.0, end_time=15.5)

        assert chunk.duration == 10.5

    def test_audio_chunk_immutable(self, tmp_path):
        """Test that AudioChunk is immutable (frozen)."""
        from pydantic import ValidationError

        chunk = AudioChunk(chunk_path=tmp_path / "test.mp3", start_time=0.0, end_time=10.0)

        with pytest.raises((ValidationError, TypeError)):
            chunk.start_time = 5.0


class TestChunkingConfig:
    """Tests for ChunkingConfig model."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ChunkingConfig()

        assert config.segment_duration == 600.0
        assert config.overlap_ms == 2000
        assert config.output_format == "mp3"
        assert config.copy_codec is False

    def test_custom_config(self):
        """Test custom configuration."""
        config = ChunkingConfig(
            segment_duration=300.0,
            overlap_ms=1000,
            output_format="wav",
            copy_codec=True,
        )

        assert config.segment_duration == 300.0
        assert config.overlap_ms == 1000
        assert config.output_format == "wav"
        assert config.copy_codec is True

    def test_overlap_must_be_less_than_segment(self):
        """Test that overlap validation works."""
        with pytest.raises(ValueError, match="overlap_ms.*must be less than"):
            ChunkingConfig(segment_duration=5.0, overlap_ms=6000)  # 6s > 5s

    def test_overlap_equal_to_segment_rejected(self):
        """Test that equal overlap/segment is rejected."""
        with pytest.raises(ValueError):
            ChunkingConfig(segment_duration=5.0, overlap_ms=5000)  # 5s = 5s


class TestDefaultChunkNamer:
    """Tests for default chunk naming function."""

    def test_basic_naming(self):
        """Test basic chunk naming."""
        name = default_chunk_namer(0, 0.0, 600.0)
        assert name == "chunk_000_0_600.mp3"

    def test_naming_with_index(self):
        """Test naming with higher index."""
        name = default_chunk_namer(5, 3000.0, 3600.0)
        assert name == "chunk_005_3000_3600.mp3"

    def test_naming_zero_padded(self):
        """Test that index is zero-padded."""
        name = default_chunk_namer(99, 0.0, 100.0)
        assert name == "chunk_099_0_100.mp3"


class TestTranscriptionConfig:
    """Tests for TranscriptionConfig model."""

    def test_default_config(self):
        """Test default transcription configuration."""
        config = TranscriptionConfig()

        assert config.model == "base"
        assert config.backend == "auto"
        assert config.device == "auto"
        assert config.language is None
        assert config.beam_size == 5
        assert config.word_timestamps is True

    def test_custom_config(self):
        """Test custom transcription configuration."""
        config = TranscriptionConfig(
            model="large-v3",
            backend="mlx",
            device="gpu",
            language="en",
            beam_size=3,
            word_timestamps=False,
        )

        assert config.model == "large-v3"
        assert config.backend == "mlx"
        assert config.device == "gpu"
        assert config.language == "en"
        assert config.beam_size == 3
        assert config.word_timestamps is False


class TestWordTiming:
    """Tests for WordTiming model."""

    def test_word_timing_creation(self):
        """Test creating a WordTiming."""
        word = WordTiming(word="hello", start_time=0.5, end_time=1.0)

        assert word.word == "hello"
        assert word.start_time == 0.5
        assert word.end_time == 1.0
        assert word.confidence is None

    def test_word_timing_with_confidence(self):
        """Test WordTiming with confidence score."""
        word = WordTiming(word="world", start_time=1.0, end_time=1.5, confidence=0.95)

        assert word.confidence == 0.95


class TestTranscriptionResult:
    """Tests for TranscriptionResult model."""

    def test_basic_result(self):
        """Test creating a basic transcription result."""
        result = TranscriptionResult(text="Hello world")

        assert result.text == "Hello world"
        assert result.language is None
        assert result.duration is None
        assert result.words == []
        assert result.segments == []
        assert result.backend_used is None
        assert result.device_used is None

    def test_full_result(self):
        """Test creating a full transcription result."""
        words = [
            WordTiming(word="Hello", start_time=0.0, end_time=0.5),
            WordTiming(word="world", start_time=0.5, end_time=1.0),
        ]
        segments = [TranscriptionSegment(id=0, text="Hello world", start_time=0.0, end_time=1.0)]

        result = TranscriptionResult(
            text="Hello world",
            language="en",
            duration=1.0,
            words=words,
            segments=segments,
            backend_used="mlx",
            device_used="metal",
        )

        assert result.text == "Hello world"
        assert result.language == "en"
        assert result.duration == 1.0
        assert len(result.words) == 2
        assert len(result.segments) == 1
        assert result.backend_used == "mlx"
        assert result.device_used == "metal"


class TestHardwareDetection:
    """Tests for hardware detection functions."""

    def test_is_apple_silicon_returns_bool(self):
        """Test that is_apple_silicon returns a boolean."""
        result = is_apple_silicon()
        assert isinstance(result, bool)

    def test_has_mlx_whisper_returns_bool(self):
        """Test that has_mlx_whisper returns a boolean."""
        result = has_mlx_whisper()
        assert isinstance(result, bool)

    def test_has_faster_whisper_returns_bool(self):
        """Test that has_faster_whisper returns a boolean."""
        result = has_faster_whisper()
        assert isinstance(result, bool)


class TestSpeakerAlignment:
    """Tests for speaker alignment functions."""

    def test_align_speakers_empty_words(self):
        """Test alignment with no words returns empty list."""
        diarization = DiarizationResult(segments=[], num_speakers=0)
        words: list[WordTiming] = []

        result = align_speakers_to_words(diarization, words)

        assert result == []

    def test_align_speakers_empty_segments(self):
        """Test alignment with no speaker segments returns empty list."""
        diarization = DiarizationResult(segments=[], num_speakers=0)
        words = [WordTiming(word="hello", start_time=0.0, end_time=0.5)]

        result = align_speakers_to_words(diarization, words)

        assert result == []

    def test_align_speakers_single_speaker(self):
        """Test alignment with single speaker."""
        segments = [SpeakerSegment(speaker_id="SPEAKER_00", start_time=0.0, end_time=10.0)]
        diarization = DiarizationResult(segments=segments, num_speakers=1)
        words = [
            WordTiming(word="hello", start_time=0.0, end_time=0.5),
            WordTiming(word="world", start_time=0.5, end_time=1.0),
        ]

        result = align_speakers_to_words(diarization, words)

        assert len(result) == 1
        assert result[0].speaker_id == "SPEAKER_00"
        assert result[0].text == "hello world"

    def test_align_speakers_multiple_speakers(self):
        """Test alignment with multiple speakers."""
        segments = [
            SpeakerSegment(speaker_id="SPEAKER_00", start_time=0.0, end_time=2.0),
            SpeakerSegment(speaker_id="SPEAKER_01", start_time=2.0, end_time=4.0),
        ]
        diarization = DiarizationResult(segments=segments, num_speakers=2)
        words = [
            WordTiming(word="hello", start_time=0.5, end_time=1.0),
            WordTiming(word="there", start_time=1.0, end_time=1.5),
            WordTiming(word="how", start_time=2.5, end_time=3.0),
            WordTiming(word="are", start_time=3.0, end_time=3.5),
        ]

        result = align_speakers_to_words(diarization, words)

        assert len(result) == 2
        assert result[0].speaker_id == "SPEAKER_00"
        assert result[0].text == "hello there"
        assert result[1].speaker_id == "SPEAKER_01"
        assert result[1].text == "how are"


class TestMergeCrossChunkSpeakers:
    """Tests for cross-chunk speaker merging."""

    def test_merge_empty_utterances(self):
        """Test merging empty utterance list."""
        segments, speaker_map = merge_cross_chunk_speakers([], [])

        assert segments == []
        assert speaker_map == {}

    def test_merge_single_chunk(self):
        """Test merging single chunk utterances."""
        utterances = [
            [
                SpeakerUtterance(
                    speaker_id="SPK1",
                    text="Hello",
                    start_time=0.0,
                    end_time=1.0,
                    words=[],
                )
            ]
        ]
        offsets = [0.0]

        segments, speaker_map = merge_cross_chunk_speakers(utterances, offsets)

        assert len(segments) == 1
        assert segments[0].speaker_id == "SPEAKER_00"
        assert segments[0].text == "Hello"

    def test_merge_consecutive_same_speaker(self):
        """Test that consecutive segments from same speaker are merged."""
        utterances = [
            [
                SpeakerUtterance(
                    speaker_id="SPK1",
                    text="Hello",
                    start_time=0.0,
                    end_time=0.5,
                    words=[],
                ),
                SpeakerUtterance(
                    speaker_id="SPK1",
                    text="world",
                    start_time=0.5,
                    end_time=1.0,
                    words=[],
                ),
            ]
        ]
        offsets = [0.0]

        segments, _ = merge_cross_chunk_speakers(utterances, offsets)

        # Should merge into single segment
        assert len(segments) == 1
        assert segments[0].text == "Hello world"


class TestFormatDiarizedTranscript:
    """Tests for transcript formatting."""

    def test_format_empty_segments(self):
        """Test formatting empty segment list."""
        result = format_diarized_transcript([])
        assert result == ""

    def test_format_single_segment(self):
        """Test formatting single segment."""
        segments = [
            TranscriptionSpeakerSegment(
                speaker_id="SPEAKER_00",
                start_time=0.0,
                end_time=1.0,
                text="Hello world",
            )
        ]

        result = format_diarized_transcript(segments)

        assert result == "[SPEAKER_00]: Hello world"

    def test_format_multiple_segments(self):
        """Test formatting multiple segments."""
        segments = [
            TranscriptionSpeakerSegment(
                speaker_id="SPEAKER_00",
                start_time=0.0,
                end_time=1.0,
                text="Hello",
            ),
            TranscriptionSpeakerSegment(
                speaker_id="SPEAKER_01",
                start_time=1.0,
                end_time=2.0,
                text="Hi there",
            ),
        ]

        result = format_diarized_transcript(segments)

        assert "[SPEAKER_00]: Hello" in result
        assert "[SPEAKER_01]: Hi there" in result


class TestUtterancesToSegments:
    """Tests for utterance conversion."""

    def test_convert_empty_list(self):
        """Test converting empty list."""
        result = utterances_to_segments([])
        assert result == []

    def test_convert_utterances(self):
        """Test converting utterances to segments."""
        utterances = [
            SpeakerUtterance(
                speaker_id="SPK1",
                text="Hello",
                start_time=0.0,
                end_time=1.0,
                words=[],
            ),
            SpeakerUtterance(
                speaker_id="SPK2",
                text="World",
                start_time=1.0,
                end_time=2.0,
                words=[],
            ),
        ]

        result = utterances_to_segments(utterances)

        assert len(result) == 2
        assert result[0].speaker_id == "SPK1"
        assert result[0].text == "Hello"
        assert result[1].speaker_id == "SPK2"
        assert result[1].text == "World"


class TestExceptions:
    """Tests for audio-related exceptions."""

    def test_transcription_error(self):
        """Test TranscriptionError can be raised."""
        with pytest.raises(TranscriptionError):
            raise TranscriptionError("Test error")

    def test_backend_not_available_error(self):
        """Test BackendNotAvailableError can be raised."""
        with pytest.raises(BackendNotAvailableError):
            raise BackendNotAvailableError("No backend installed")

    def test_backend_error_is_transcription_error(self):
        """Test that BackendNotAvailableError is a TranscriptionError."""
        assert issubclass(BackendNotAvailableError, TranscriptionError)
