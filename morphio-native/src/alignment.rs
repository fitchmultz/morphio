use crate::types::*;
use intervaltree::{Element, IntervalTree};
use pyo3::prelude::*;
use std::collections::HashMap;

fn to_micros(t: f64) -> i64 {
    (t * 1_000_000.0) as i64
}

/// Find speaker with MAX OVERLAP (matches Python semantics exactly)
/// Uses SpeakerSegmentInput for FromPyObject compatibility
#[pyfunction]
pub fn find_overlapping_speaker(
    word_start: f64,
    word_end: f64,
    segments: Vec<SpeakerSegmentInput>, // Input type, not output type
) -> Option<String> {
    let mut best_speaker: Option<String> = None;
    let mut best_overlap = 0.0;

    for segment in &segments {
        let overlap_start = word_start.max(segment.start_time);
        let overlap_end = word_end.min(segment.end_time);
        let overlap = (overlap_end - overlap_start).max(0.0);

        if overlap > best_overlap {
            best_overlap = overlap;
            best_speaker = Some(segment.speaker_id.clone());
        }
    }

    best_speaker
}

/// Align speakers using interval tree for O(log n) lookup
/// Uses Input types for FromPyObject compatibility
#[pyfunction]
pub fn align_speakers_to_words(
    segments: Vec<SpeakerSegmentInput>,
    words: Vec<WordTimingInput>,
) -> Vec<SpeakerUtterance> {
    if segments.is_empty() || words.is_empty() {
        return vec![];
    }

    // Build interval tree: O(n log n)
    let tree: IntervalTree<i64, usize> = segments
        .iter()
        .enumerate()
        .map(|(idx, s)| Element {
            range: to_micros(s.start_time)..to_micros(s.end_time),
            value: idx,
        })
        .collect();

    let mut utterances: Vec<SpeakerUtterance> = Vec::new();
    let mut current_speaker: Option<String> = None;
    let mut current_words: Vec<WordTiming> = Vec::new();
    let mut current_start: f64 = 0.0;

    for word in words {
        // Find overlapping segments via interval tree
        let word_start_us = to_micros(word.start_time);
        let word_end_us = to_micros(word.end_time);

        // Find MAX OVERLAP speaker (Python semantics)
        let speaker = {
            let mut best_speaker: Option<String> = None;
            let mut best_overlap = 0.0;

            for element in tree.query(word_start_us..word_end_us) {
                let seg = &segments[element.value];
                let overlap_start = word.start_time.max(seg.start_time);
                let overlap_end = word.end_time.min(seg.end_time);
                let overlap = (overlap_end - overlap_start).max(0.0);

                if overlap > best_overlap {
                    best_overlap = overlap;
                    best_speaker = Some(seg.speaker_id.clone());
                }
            }
            best_speaker
        };

        let speaker = match speaker {
            Some(s) => s,
            None => {
                // No speaker found - use PREVIOUS speaker (matches Python)
                if let Some(ref s) = current_speaker {
                    s.clone()
                } else {
                    continue;
                }
            }
        };

        if Some(&speaker) != current_speaker.as_ref() {
            // Speaker changed - finalize current utterance
            if !current_words.is_empty() {
                let text = current_words
                    .iter()
                    .map(|w| w.word.as_str())
                    .collect::<Vec<_>>()
                    .join(" ");
                let end_time = current_words
                    .last()
                    .map(|w| w.end_time)
                    .unwrap_or(current_start);
                utterances.push(SpeakerUtterance::new(
                    current_speaker
                        .clone()
                        .unwrap_or_else(|| "UNKNOWN".to_string()),
                    text,
                    current_start,
                    end_time,
                    std::mem::take(&mut current_words),
                ));
            }
            current_speaker = Some(speaker);
            current_start = word.start_time;
        }

        current_words.push(WordTiming::new(
            word.word,
            word.start_time,
            word.end_time,
            word.confidence,
        ));
    }

    // Finalize last utterance
    if !current_words.is_empty() {
        if let Some(speaker) = current_speaker {
            let text = current_words
                .iter()
                .map(|w| w.word.as_str())
                .collect::<Vec<_>>()
                .join(" ");
            let end_time = current_words
                .last()
                .map(|w| w.end_time)
                .unwrap_or(current_start);
            utterances.push(SpeakerUtterance::new(
                speaker,
                text,
                current_start,
                end_time,
                current_words,
            ));
        }
    }

    utterances
}

/// Merge cross-chunk speakers - RETURNS TUPLE (segments, mapping)
/// Uses Input types for FromPyObject compatibility
#[pyfunction]
pub fn merge_cross_chunk_speakers(
    chunk_utterances: Vec<Vec<SpeakerUtteranceInput>>,
    chunk_offsets: Vec<f64>,
) -> (Vec<TranscriptionSpeakerSegment>, HashMap<String, String>) {
    if chunk_utterances.is_empty() {
        return (vec![], HashMap::new());
    }

    let mut all_segments: Vec<TranscriptionSpeakerSegment> = Vec::new();
    let mut global_speaker_map: HashMap<String, String> = HashMap::new();
    let mut speaker_counter: usize = 0;

    const CONTINUATION_THRESHOLD: f64 = 2.0;

    for (chunk_idx, (utterances, offset)) in chunk_utterances
        .iter()
        .zip(chunk_offsets.iter())
        .enumerate()
    {
        let mut chunk_speaker_map: HashMap<String, String> = HashMap::new();

        for utterance in utterances {
            let global_id = if let Some(mapped) = chunk_speaker_map.get(&utterance.speaker_id) {
                mapped.clone()
            } else if chunk_idx > 0 && !all_segments.is_empty() {
                let last = all_segments.last().unwrap();
                let time_gap = (utterance.start_time + offset) - last.end_time;

                if time_gap < CONTINUATION_THRESHOLD {
                    let id = last.speaker_id.clone();
                    chunk_speaker_map.insert(utterance.speaker_id.clone(), id.clone());
                    id
                } else {
                    let id = format!("SPEAKER_{:02}", speaker_counter);
                    speaker_counter += 1;
                    chunk_speaker_map.insert(utterance.speaker_id.clone(), id.clone());
                    global_speaker_map.insert(utterance.speaker_id.clone(), id.clone());
                    id
                }
            } else {
                let id = format!("SPEAKER_{:02}", speaker_counter);
                speaker_counter += 1;
                chunk_speaker_map.insert(utterance.speaker_id.clone(), id.clone());
                global_speaker_map.insert(utterance.speaker_id.clone(), id.clone());
                id
            };

            all_segments.push(TranscriptionSpeakerSegment::new(
                global_id,
                utterance.start_time + offset,
                utterance.end_time + offset,
                utterance.text.clone(),
            ));
        }
    }

    // Merge consecutive same-speaker segments
    let mut merged: Vec<TranscriptionSpeakerSegment> = Vec::with_capacity(all_segments.len());
    for segment in all_segments {
        if let Some(last) = merged.last_mut() {
            if last.speaker_id == segment.speaker_id {
                last.end_time = segment.end_time;
                // Append text with space
                let mut new_text = last.text.clone();
                new_text.push(' ');
                new_text.push_str(&segment.text);
                last.text = new_text;
                continue;
            }
        }
        merged.push(segment);
    }

    (merged, global_speaker_map)
}

/// Uses Input types for FromPyObject compatibility
#[pyfunction]
pub fn format_diarized_transcript(segments: Vec<TranscriptionSpeakerSegmentInput>) -> String {
    let total_len: usize = segments
        .iter()
        .map(|s| s.speaker_id.len() + s.text.len() + 5)
        .sum();

    let mut result = String::with_capacity(total_len);
    for (i, segment) in segments.iter().enumerate() {
        if i > 0 {
            result.push('\n');
        }
        result.push('[');
        result.push_str(&segment.speaker_id);
        result.push_str("]: ");
        result.push_str(&segment.text);
    }
    result
}

/// Uses Input types for FromPyObject compatibility
#[pyfunction]
pub fn utterances_to_segments(
    utterances: Vec<SpeakerUtteranceInput>,
) -> Vec<TranscriptionSpeakerSegment> {
    utterances
        .into_iter()
        .map(|u| TranscriptionSpeakerSegment::new(u.speaker_id, u.start_time, u.end_time, u.text))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_segment(speaker_id: &str, start: f64, end: f64) -> SpeakerSegmentInput {
        SpeakerSegmentInput {
            speaker_id: speaker_id.to_string(),
            start_time: start,
            end_time: end,
            confidence: Some(0.9),
        }
    }

    fn make_word(word: &str, start: f64, end: f64) -> WordTimingInput {
        WordTimingInput {
            word: word.to_string(),
            start_time: start,
            end_time: end,
            confidence: Some(0.95),
        }
    }

    #[test]
    fn test_find_overlapping_speaker_max_overlap() {
        let segments = vec![
            make_segment("SPEAKER_00", 0.0, 5.0),
            make_segment("SPEAKER_01", 4.0, 10.0),
        ];

        // Word from 4.5 to 5.5 overlaps both speakers
        // SPEAKER_00: 4.5 to 5.0 = 0.5s overlap
        // SPEAKER_01: 4.5 to 5.5 = 1.0s overlap (but clamped to 5.0..5.5 = 0.5s for SPEAKER_01 start at 4.0)
        // Actually: SPEAKER_01 overlap = min(5.5, 10.0) - max(4.5, 4.0) = 5.5 - 4.5 = 1.0s
        let result = find_overlapping_speaker(4.5, 5.5, segments);
        assert_eq!(result, Some("SPEAKER_01".to_string()));
    }

    #[test]
    fn test_find_overlapping_speaker_no_overlap() {
        let segments = vec![make_segment("SPEAKER_00", 0.0, 5.0)];

        let result = find_overlapping_speaker(10.0, 11.0, segments);
        assert_eq!(result, None);
    }

    #[test]
    fn test_align_speakers_to_words_basic() {
        let segments = vec![
            make_segment("SPEAKER_00", 0.0, 5.0),
            make_segment("SPEAKER_01", 5.0, 10.0),
        ];
        let words = vec![
            make_word("Hello", 0.0, 0.5),
            make_word("world", 0.5, 1.0),
            make_word("How", 5.0, 5.5),
            make_word("are", 5.5, 6.0),
        ];

        let result = align_speakers_to_words(segments, words);

        assert_eq!(result.len(), 2);
        assert_eq!(result[0].speaker_id, "SPEAKER_00");
        assert_eq!(result[0].text, "Hello world");
        assert_eq!(result[1].speaker_id, "SPEAKER_01");
        assert_eq!(result[1].text, "How are");
    }

    #[test]
    fn test_align_speakers_empty_inputs() {
        let result = align_speakers_to_words(vec![], vec![]);
        assert!(result.is_empty());
    }

    #[test]
    fn test_format_diarized_transcript() {
        let segments = vec![
            TranscriptionSpeakerSegmentInput {
                speaker_id: "SPEAKER_00".to_string(),
                start_time: 0.0,
                end_time: 5.0,
                text: "Hello world".to_string(),
            },
            TranscriptionSpeakerSegmentInput {
                speaker_id: "SPEAKER_01".to_string(),
                start_time: 5.0,
                end_time: 10.0,
                text: "How are you".to_string(),
            },
        ];

        let result = format_diarized_transcript(segments);
        assert_eq!(
            result,
            "[SPEAKER_00]: Hello world\n[SPEAKER_01]: How are you"
        );
    }

    #[test]
    fn test_utterances_to_segments() {
        let utterances = vec![SpeakerUtteranceInput {
            speaker_id: "SPEAKER_00".to_string(),
            text: "Hello".to_string(),
            start_time: 0.0,
            end_time: 1.0,
            words: vec![make_word("Hello", 0.0, 1.0)],
        }];

        let result = utterances_to_segments(utterances);
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].speaker_id, "SPEAKER_00");
        assert_eq!(result[0].text, "Hello");
    }
}
