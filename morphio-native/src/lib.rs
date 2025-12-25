#[allow(clippy::useless_conversion)]
mod alignment;
#[allow(clippy::useless_conversion)]
mod anonymizer;
mod types;

use pyo3::prelude::*;

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Anonymizer
    m.add_function(wrap_pyfunction!(anonymizer::anonymize, m)?)?;
    m.add_class::<types::AnonymizationResult>()?;

    // Alignment
    m.add_function(wrap_pyfunction!(alignment::find_overlapping_speaker, m)?)?;
    m.add_function(wrap_pyfunction!(alignment::align_speakers_to_words, m)?)?;
    m.add_function(wrap_pyfunction!(alignment::merge_cross_chunk_speakers, m)?)?;
    m.add_function(wrap_pyfunction!(alignment::format_diarized_transcript, m)?)?;
    m.add_function(wrap_pyfunction!(alignment::utterances_to_segments, m)?)?;
    m.add_class::<types::SpeakerSegment>()?;
    m.add_class::<types::WordTiming>()?;
    m.add_class::<types::SpeakerUtterance>()?;
    m.add_class::<types::TranscriptionSpeakerSegment>()?;

    Ok(())
}
