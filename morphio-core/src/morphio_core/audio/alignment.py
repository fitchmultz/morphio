"""
Speaker-to-text alignment service.

Aligns diarization speaker segments with transcription word timings
to produce speaker-attributed transcriptions.
"""

from .types import (
    DiarizationResult,
    SpeakerSegment,
    SpeakerUtterance,
    TranscriptionSpeakerSegment,
    WordTiming,
)


def find_overlapping_speaker(
    word_start: float,
    word_end: float,
    segments: list[SpeakerSegment],
) -> str | None:
    """
    Find the speaker whose segment overlaps most with the given word timing.

    Uses overlap duration to handle edge cases where words span segment boundaries.

    Args:
        word_start: Word start time in seconds
        word_end: Word end time in seconds
        segments: List of speaker segments from diarization

    Returns:
        Speaker ID of the best matching speaker, or None if no overlap
    """
    best_speaker = None
    best_overlap = 0.0

    for segment in segments:
        # Calculate overlap between word and segment
        overlap_start = max(word_start, segment.start_time)
        overlap_end = min(word_end, segment.end_time)
        overlap = max(0, overlap_end - overlap_start)

        if overlap > best_overlap:
            best_overlap = overlap
            best_speaker = segment.speaker_id

    return best_speaker


def align_speakers_to_words(
    diarization: DiarizationResult,
    words: list[WordTiming],
) -> list[SpeakerUtterance]:
    """
    Align speaker segments with word timings to produce speaker utterances.

    Groups consecutive words from the same speaker into utterances.

    Args:
        diarization: Diarization result with speaker segments
        words: List of word timings from transcription

    Returns:
        List of speaker utterances with aligned text
    """
    if not words or not diarization.segments:
        return []

    utterances: list[SpeakerUtterance] = []
    current_speaker: str | None = None
    current_words: list[WordTiming] = []
    current_start: float = 0.0

    for word in words:
        speaker = find_overlapping_speaker(word.start_time, word.end_time, diarization.segments)

        if speaker is None:
            # No speaker found - use previous speaker or skip
            if current_speaker:
                speaker = current_speaker
            else:
                continue

        if speaker != current_speaker:
            # Speaker changed - finalize current utterance
            if current_words:
                utterances.append(
                    SpeakerUtterance(
                        speaker_id=current_speaker or "UNKNOWN",
                        text=" ".join(w.word for w in current_words),
                        start_time=current_start,
                        end_time=current_words[-1].end_time,
                        words=current_words,
                    )
                )

            current_speaker = speaker
            current_words = [word]
            current_start = word.start_time
        else:
            current_words.append(word)

    # Finalize last utterance
    if current_words and current_speaker:
        utterances.append(
            SpeakerUtterance(
                speaker_id=current_speaker,
                text=" ".join(w.word for w in current_words),
                start_time=current_start,
                end_time=current_words[-1].end_time,
                words=current_words,
            )
        )

    return utterances


def merge_cross_chunk_speakers(
    chunk_utterances: list[list[SpeakerUtterance]],
    chunk_offsets: list[float],
) -> tuple[list[TranscriptionSpeakerSegment], dict[str, str]]:
    """
    Merge speaker utterances across chunks, handling speaker ID consistency.

    When chunks are processed independently, the same speaker may get different
    IDs in different chunks. This function attempts to merge them based on
    temporal proximity (speakers close in time are likely the same person).

    Args:
        chunk_utterances: List of utterance lists, one per chunk
        chunk_offsets: Start time offset for each chunk in seconds

    Returns:
        Tuple of (merged segments, speaker mapping)
    """
    if not chunk_utterances:
        return [], {}

    all_segments: list[TranscriptionSpeakerSegment] = []
    global_speaker_map: dict[str, str] = {}
    speaker_counter = 0

    for chunk_idx, (utterances, offset) in enumerate(
        zip(chunk_utterances, chunk_offsets, strict=False)
    ):
        chunk_speaker_map: dict[str, str] = {}

        for utterance in utterances:
            # Map local speaker ID to global ID
            if utterance.speaker_id not in chunk_speaker_map:
                # Check if this might be a continuation from previous chunk
                if chunk_idx > 0 and all_segments:
                    last_segment = all_segments[-1]
                    time_gap = (utterance.start_time + offset) - last_segment.end_time

                    # If small gap (< 2 seconds), likely same speaker continuing
                    if time_gap < 2.0:
                        chunk_speaker_map[utterance.speaker_id] = last_segment.speaker_id
                    else:
                        # New speaker
                        global_id = f"SPEAKER_{speaker_counter:02d}"
                        chunk_speaker_map[utterance.speaker_id] = global_id
                        global_speaker_map[utterance.speaker_id] = global_id
                        speaker_counter += 1
                else:
                    global_id = f"SPEAKER_{speaker_counter:02d}"
                    chunk_speaker_map[utterance.speaker_id] = global_id
                    global_speaker_map[utterance.speaker_id] = global_id
                    speaker_counter += 1

            global_speaker_id = chunk_speaker_map[utterance.speaker_id]

            # Create output segment with adjusted times
            all_segments.append(
                TranscriptionSpeakerSegment(
                    speaker_id=global_speaker_id,
                    start_time=utterance.start_time + offset,
                    end_time=utterance.end_time + offset,
                    text=utterance.text,
                )
            )

    # Merge consecutive segments from same speaker
    merged_segments: list[TranscriptionSpeakerSegment] = []
    for segment in all_segments:
        if merged_segments and merged_segments[-1].speaker_id == segment.speaker_id:
            # Merge with previous segment
            last = merged_segments[-1]
            merged_segments[-1] = TranscriptionSpeakerSegment(
                speaker_id=last.speaker_id,
                start_time=last.start_time,
                end_time=segment.end_time,
                text=f"{last.text} {segment.text}",
            )
        else:
            merged_segments.append(segment)

    return merged_segments, global_speaker_map


def format_diarized_transcript(segments: list[TranscriptionSpeakerSegment]) -> str:
    """
    Format speaker segments into a readable transcript with inline labels.

    Example output:
    [SPEAKER_00]: Hello, how are you?
    [SPEAKER_01]: I'm doing well, thanks for asking.
    [SPEAKER_00]: Great to hear!

    Args:
        segments: List of speaker segments with text

    Returns:
        Formatted transcript string with speaker labels
    """
    lines = []
    for segment in segments:
        lines.append(f"[{segment.speaker_id}]: {segment.text}")
    return "\n".join(lines)


def utterances_to_segments(
    utterances: list[SpeakerUtterance],
) -> list[TranscriptionSpeakerSegment]:
    """
    Convert utterances to transcription speaker segments.

    Args:
        utterances: List of speaker utterances

    Returns:
        List of transcription speaker segments
    """
    return [
        TranscriptionSpeakerSegment(
            speaker_id=u.speaker_id,
            start_time=u.start_time,
            end_time=u.end_time,
            text=u.text,
        )
        for u in utterances
    ]
