"""
Unit tests for the speaker alignment service.
"""

from app.schemas.diarization_schema import (
    DiarizationResult,
    SpeakerSegment,
    SpeakerUtterance,
    TranscriptionSpeakerSegment,
    WordTiming,
)
from app.services.audio.speaker_alignment import (
    align_speakers_to_words,
    find_overlapping_speaker,
    format_diarized_transcript,
    merge_cross_chunk_speakers,
    utterances_to_segments,
)


class TestFindOverlappingSpeaker:
    """Tests for find_overlapping_speaker function."""

    def test_word_fully_in_segment(self):
        """Test word completely within a speaker segment."""
        segments = [
            SpeakerSegment(speaker_id="SPEAKER_00", start_time=0.0, end_time=5.0),
            SpeakerSegment(speaker_id="SPEAKER_01", start_time=5.0, end_time=10.0),
        ]
        speaker = find_overlapping_speaker(1.0, 1.5, segments)
        assert speaker == "SPEAKER_00"

    def test_word_in_second_segment(self):
        """Test word in the second speaker segment."""
        segments = [
            SpeakerSegment(speaker_id="SPEAKER_00", start_time=0.0, end_time=5.0),
            SpeakerSegment(speaker_id="SPEAKER_01", start_time=5.0, end_time=10.0),
        ]
        speaker = find_overlapping_speaker(6.0, 6.5, segments)
        assert speaker == "SPEAKER_01"

    def test_word_spans_boundary(self):
        """Test word that spans the boundary between two segments."""
        segments = [
            SpeakerSegment(speaker_id="SPEAKER_00", start_time=0.0, end_time=5.0),
            SpeakerSegment(speaker_id="SPEAKER_01", start_time=5.0, end_time=10.0),
        ]
        # Word from 4.7 to 5.3 overlaps more with SPEAKER_00 (0.3s) than SPEAKER_01 (0.3s)
        # Actually equal, but 00 comes first so it should return 00
        speaker = find_overlapping_speaker(4.7, 5.3, segments)
        assert speaker in ["SPEAKER_00", "SPEAKER_01"]

    def test_word_spans_boundary_prefers_larger_overlap(self):
        """Test that word spanning boundary returns speaker with larger overlap."""
        segments = [
            SpeakerSegment(speaker_id="SPEAKER_00", start_time=0.0, end_time=5.0),
            SpeakerSegment(speaker_id="SPEAKER_01", start_time=5.0, end_time=10.0),
        ]
        # Word from 4.0 to 5.1 overlaps more with SPEAKER_00 (1.0s) than SPEAKER_01 (0.1s)
        speaker = find_overlapping_speaker(4.0, 5.1, segments)
        assert speaker == "SPEAKER_00"

    def test_no_overlap(self):
        """Test word with no overlapping segment."""
        segments = [
            SpeakerSegment(speaker_id="SPEAKER_00", start_time=0.0, end_time=5.0),
        ]
        speaker = find_overlapping_speaker(10.0, 10.5, segments)
        assert speaker is None

    def test_empty_segments(self):
        """Test with empty segments list."""
        speaker = find_overlapping_speaker(1.0, 1.5, [])
        assert speaker is None


class TestAlignSpeakersToWords:
    """Tests for align_speakers_to_words function."""

    def test_simple_alignment(self):
        """Test basic speaker-to-word alignment."""
        diarization = DiarizationResult(
            segments=[
                SpeakerSegment(speaker_id="SPEAKER_00", start_time=0.0, end_time=3.0),
                SpeakerSegment(speaker_id="SPEAKER_01", start_time=3.0, end_time=6.0),
            ],
            num_speakers=2,
        )
        words = [
            WordTiming(word="Hello", start_time=0.0, end_time=0.5),
            WordTiming(word="there", start_time=0.6, end_time=1.0),
            WordTiming(word="Hi", start_time=3.0, end_time=3.3),
            WordTiming(word="yourself", start_time=3.4, end_time=4.0),
        ]
        utterances = align_speakers_to_words(diarization, words)
        assert len(utterances) == 2
        assert utterances[0].speaker_id == "SPEAKER_00"
        assert utterances[0].text == "Hello there"
        assert utterances[1].speaker_id == "SPEAKER_01"
        assert utterances[1].text == "Hi yourself"

    def test_empty_words(self):
        """Test with empty words list."""
        diarization = DiarizationResult(
            segments=[
                SpeakerSegment(speaker_id="SPEAKER_00", start_time=0.0, end_time=5.0),
            ],
            num_speakers=1,
        )
        utterances = align_speakers_to_words(diarization, [])
        assert utterances == []

    def test_empty_segments(self):
        """Test with empty segments."""
        diarization = DiarizationResult(segments=[], num_speakers=0)
        words = [
            WordTiming(word="Hello", start_time=0.0, end_time=0.5),
        ]
        utterances = align_speakers_to_words(diarization, words)
        assert utterances == []

    def test_single_speaker(self):
        """Test with single speaker throughout."""
        diarization = DiarizationResult(
            segments=[
                SpeakerSegment(speaker_id="SPEAKER_00", start_time=0.0, end_time=10.0),
            ],
            num_speakers=1,
        )
        words = [
            WordTiming(word="Hello", start_time=0.0, end_time=0.5),
            WordTiming(word="world", start_time=0.6, end_time=1.0),
            WordTiming(word="how", start_time=1.1, end_time=1.3),
            WordTiming(word="are", start_time=1.4, end_time=1.6),
            WordTiming(word="you", start_time=1.7, end_time=2.0),
        ]
        utterances = align_speakers_to_words(diarization, words)
        assert len(utterances) == 1
        assert utterances[0].speaker_id == "SPEAKER_00"
        assert utterances[0].text == "Hello world how are you"
        assert len(utterances[0].words) == 5

    def test_multiple_speaker_turns(self):
        """Test with multiple speaker turns."""
        diarization = DiarizationResult(
            segments=[
                SpeakerSegment(speaker_id="SPEAKER_00", start_time=0.0, end_time=2.0),
                SpeakerSegment(speaker_id="SPEAKER_01", start_time=2.0, end_time=4.0),
                SpeakerSegment(speaker_id="SPEAKER_00", start_time=4.0, end_time=6.0),
            ],
            num_speakers=2,
        )
        words = [
            WordTiming(word="Hi", start_time=0.0, end_time=0.3),
            WordTiming(word="Hello", start_time=2.0, end_time=2.5),
            WordTiming(word="Bye", start_time=4.0, end_time=4.3),
        ]
        utterances = align_speakers_to_words(diarization, words)
        assert len(utterances) == 3
        assert utterances[0].speaker_id == "SPEAKER_00"
        assert utterances[0].text == "Hi"
        assert utterances[1].speaker_id == "SPEAKER_01"
        assert utterances[1].text == "Hello"
        assert utterances[2].speaker_id == "SPEAKER_00"
        assert utterances[2].text == "Bye"


class TestMergeCrossChunkSpeakers:
    """Tests for merge_cross_chunk_speakers function."""

    def test_single_chunk(self):
        """Test merging with a single chunk."""
        utterances = [
            SpeakerUtterance(
                speaker_id="SPEAKER_00",
                text="Hello world",
                start_time=0.0,
                end_time=1.0,
            ),
        ]
        segments, speaker_map = merge_cross_chunk_speakers([[*utterances]], [0.0])
        assert len(segments) == 1
        assert segments[0].speaker_id == "SPEAKER_00"
        assert segments[0].text == "Hello world"

    def test_two_chunks_same_speaker_continues(self):
        """Test that speakers continuing across chunks are merged."""
        chunk1 = [
            SpeakerUtterance(
                speaker_id="SPEAKER_00",
                text="Hello",
                start_time=0.0,
                end_time=1.0,
            ),
        ]
        chunk2 = [
            SpeakerUtterance(
                speaker_id="SPEAKER_00",
                text="world",
                start_time=0.0,  # Relative to chunk start
                end_time=1.0,
            ),
        ]
        # Chunk 2 starts at 1.5 seconds (small gap)
        segments, speaker_map = merge_cross_chunk_speakers([chunk1, chunk2], [0.0, 1.5])
        # Should merge consecutive same-speaker segments
        assert len(segments) == 1
        assert segments[0].text == "Hello world"

    def test_two_chunks_different_speakers(self):
        """Test two chunks with different speakers."""
        chunk1 = [
            SpeakerUtterance(
                speaker_id="SPEAKER_00",
                text="Hello",
                start_time=0.0,
                end_time=1.0,
            ),
        ]
        chunk2 = [
            SpeakerUtterance(
                speaker_id="SPEAKER_01",
                text="Hi there",
                start_time=0.0,
                end_time=1.0,
            ),
        ]
        # Large gap suggests different speaker
        segments, speaker_map = merge_cross_chunk_speakers([chunk1, chunk2], [0.0, 5.0])
        assert len(segments) == 2
        assert segments[0].speaker_id == "SPEAKER_00"
        assert segments[1].speaker_id == "SPEAKER_01"

    def test_empty_chunks(self):
        """Test with empty chunks."""
        segments, speaker_map = merge_cross_chunk_speakers([], [])
        assert segments == []
        assert speaker_map == {}


class TestFormatDiarizedTranscript:
    """Tests for format_diarized_transcript function."""

    def test_format_single_segment(self):
        """Test formatting a single speaker segment."""
        segments = [
            TranscriptionSpeakerSegment(
                speaker_id="SPEAKER_00",
                start_time=0.0,
                end_time=3.0,
                text="Hello, how are you?",
            ),
        ]
        formatted = format_diarized_transcript(segments)
        assert formatted == "[SPEAKER_00]: Hello, how are you?"

    def test_format_multiple_segments(self):
        """Test formatting multiple speaker segments."""
        segments = [
            TranscriptionSpeakerSegment(
                speaker_id="SPEAKER_00",
                start_time=0.0,
                end_time=1.5,
                text="Hello, how are you?",
            ),
            TranscriptionSpeakerSegment(
                speaker_id="SPEAKER_01",
                start_time=1.8,
                end_time=3.2,
                text="I'm doing well, thanks.",
            ),
            TranscriptionSpeakerSegment(
                speaker_id="SPEAKER_00",
                start_time=3.5,
                end_time=4.5,
                text="Great to hear!",
            ),
        ]
        formatted = format_diarized_transcript(segments)
        expected = (
            "[SPEAKER_00]: Hello, how are you?\n"
            "[SPEAKER_01]: I'm doing well, thanks.\n"
            "[SPEAKER_00]: Great to hear!"
        )
        assert formatted == expected

    def test_format_empty_segments(self):
        """Test formatting empty segments."""
        formatted = format_diarized_transcript([])
        assert formatted == ""


class TestUtterancesToSegments:
    """Tests for utterances_to_segments function."""

    def test_convert_utterances(self):
        """Test converting utterances to transcription segments."""
        utterances = [
            SpeakerUtterance(
                speaker_id="SPEAKER_00",
                text="Hello world",
                start_time=0.0,
                end_time=1.0,
                words=[
                    WordTiming(word="Hello", start_time=0.0, end_time=0.5),
                    WordTiming(word="world", start_time=0.5, end_time=1.0),
                ],
            ),
            SpeakerUtterance(
                speaker_id="SPEAKER_01",
                text="Hi there",
                start_time=1.5,
                end_time=2.5,
                words=[],
            ),
        ]
        segments = utterances_to_segments(utterances)
        assert len(segments) == 2
        assert isinstance(segments[0], TranscriptionSpeakerSegment)
        assert segments[0].speaker_id == "SPEAKER_00"
        assert segments[0].text == "Hello world"
        assert segments[0].start_time == 0.0
        assert segments[0].end_time == 1.0
        assert segments[1].speaker_id == "SPEAKER_01"
        assert segments[1].text == "Hi there"

    def test_convert_empty_utterances(self):
        """Test converting empty utterances list."""
        segments = utterances_to_segments([])
        assert segments == []
