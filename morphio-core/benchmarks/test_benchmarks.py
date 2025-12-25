"""Performance benchmarks for Rust native extension.

Run with: uv run pytest morphio-core/benchmarks -v --benchmark-only
"""

import pytest
from morphio_native import (
    align_speakers_to_words,
    anonymize,
    find_overlapping_speaker,
    format_diarized_transcript,
    merge_cross_chunk_speakers,
    utterances_to_segments,
)

from morphio_core.audio.types import (
    SpeakerSegment,
    SpeakerUtterance,
    TranscriptionSpeakerSegment,
    WordTiming,
)

# =============================================================================
# Data Generators
# =============================================================================


def generate_alignment_data(n_segments: int, n_words: int):
    """Generate test data for alignment benchmarks."""
    segments = [
        SpeakerSegment(
            speaker_id=f"SPEAKER_{i % 3:02d}",
            start_time=i * 2.0,
            end_time=(i + 1) * 2.0,
            confidence=0.9,
        )
        for i in range(n_segments)
    ]
    words = [
        WordTiming(
            word=f"word{i}",
            start_time=i * 0.1,
            end_time=i * 0.1 + 0.08,
            confidence=0.95,
        )
        for i in range(n_words)
    ]
    return segments, words


def generate_utterances(n_utterances: int, words_per_utterance: int = 10):
    """Generate test data for utterance benchmarks."""
    utterances = []
    for i in range(n_utterances):
        start = i * 2.0
        words = [
            WordTiming(
                word=f"word{j}",
                start_time=start + j * 0.1,
                end_time=start + j * 0.1 + 0.08,
                confidence=0.95,
            )
            for j in range(words_per_utterance)
        ]
        utterances.append(
            SpeakerUtterance(
                speaker_id=f"SPEAKER_{i % 3:02d}",
                text=" ".join(f"word{j}" for j in range(words_per_utterance)),
                start_time=start,
                end_time=start + words_per_utterance * 0.1,
                words=words,
            )
        )
    return utterances


def generate_segments(n_segments: int):
    """Generate test data for format benchmarks."""
    return [
        TranscriptionSpeakerSegment(
            speaker_id=f"SPEAKER_{i % 3:02d}",
            start_time=i * 2.0,
            end_time=(i + 1) * 2.0,
            text=f"This is segment {i} with some example text content.",
        )
        for i in range(n_segments)
    ]


def generate_anonymization_content(size_kb: int):
    """Generate content with PII for anonymization benchmarks."""
    base = (
        "Contact john.doe@example.com or call 555-123-4567. "
        "Server IP: 192.168.1.100. SSN: 123-45-6789. "
        "Card: 4111-1111-1111-1111. "
    )
    # Repeat to reach desired size
    repeat_count = (size_kb * 1024) // len(base) + 1
    return base * repeat_count


# =============================================================================
# Alignment Benchmarks
# =============================================================================


@pytest.mark.benchmark(group="alignment")
def test_align_1k_words_100_segments(benchmark):
    """Benchmark alignment with 1,000 words and 100 speaker segments."""
    segments, words = generate_alignment_data(100, 1000)
    benchmark(align_speakers_to_words, segments, words)


@pytest.mark.benchmark(group="alignment")
def test_align_10k_words_1k_segments(benchmark):
    """Benchmark alignment with 10,000 words and 1,000 speaker segments."""
    segments, words = generate_alignment_data(1000, 10000)
    benchmark(align_speakers_to_words, segments, words)


@pytest.mark.benchmark(group="alignment")
def test_find_overlapping_100_segments(benchmark):
    """Benchmark single word overlap lookup with 100 segments."""
    segments, _ = generate_alignment_data(100, 0)
    benchmark(find_overlapping_speaker, 50.0, 50.5, segments)


@pytest.mark.benchmark(group="alignment")
def test_find_overlapping_1k_segments(benchmark):
    """Benchmark single word overlap lookup with 1,000 segments."""
    segments, _ = generate_alignment_data(1000, 0)
    benchmark(find_overlapping_speaker, 500.0, 500.5, segments)


# =============================================================================
# Merge Benchmarks
# =============================================================================


@pytest.mark.benchmark(group="merge")
def test_merge_10_chunks_100_utterances(benchmark):
    """Benchmark merging 10 chunks with 100 utterances each."""
    chunks = [generate_utterances(100) for _ in range(10)]
    offsets = [i * 200.0 for i in range(10)]
    benchmark(merge_cross_chunk_speakers, chunks, offsets)


@pytest.mark.benchmark(group="merge")
def test_merge_50_chunks_50_utterances(benchmark):
    """Benchmark merging 50 chunks with 50 utterances each."""
    chunks = [generate_utterances(50) for _ in range(50)]
    offsets = [i * 100.0 for i in range(50)]
    benchmark(merge_cross_chunk_speakers, chunks, offsets)


# =============================================================================
# Format Benchmarks
# =============================================================================


@pytest.mark.benchmark(group="format")
def test_format_100_segments(benchmark):
    """Benchmark formatting 100 transcript segments."""
    segments = generate_segments(100)
    benchmark(format_diarized_transcript, segments)


@pytest.mark.benchmark(group="format")
def test_format_1k_segments(benchmark):
    """Benchmark formatting 1,000 transcript segments."""
    segments = generate_segments(1000)
    benchmark(format_diarized_transcript, segments)


# =============================================================================
# Utterances to Segments Benchmarks
# =============================================================================


@pytest.mark.benchmark(group="convert")
def test_utterances_to_segments_100(benchmark):
    """Benchmark converting 100 utterances to segments."""
    utterances = generate_utterances(100)
    benchmark(utterances_to_segments, utterances)


@pytest.mark.benchmark(group="convert")
def test_utterances_to_segments_1k(benchmark):
    """Benchmark converting 1,000 utterances to segments."""
    utterances = generate_utterances(1000)
    benchmark(utterances_to_segments, utterances)


# =============================================================================
# Anonymization Benchmarks
# =============================================================================


@pytest.mark.benchmark(group="anonymize")
def test_anonymize_1kb(benchmark):
    """Benchmark anonymizing 1KB of content with PII."""
    content = generate_anonymization_content(1)
    benchmark(anonymize, content)


@pytest.mark.benchmark(group="anonymize")
def test_anonymize_100kb(benchmark):
    """Benchmark anonymizing 100KB of content with PII."""
    content = generate_anonymization_content(100)
    benchmark(anonymize, content)


@pytest.mark.benchmark(group="anonymize")
def test_anonymize_1mb(benchmark):
    """Benchmark anonymizing 1MB of content with PII."""
    content = generate_anonymization_content(1024)
    benchmark(anonymize, content)
