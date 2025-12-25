use pyo3::prelude::*;
use std::collections::HashMap;

#[pyclass]
#[derive(Clone)]
pub struct AnonymizationResult {
    #[pyo3(get)]
    pub text: String,
    #[pyo3(get)]
    pub mapping: HashMap<String, String>,
    #[pyo3(get)]
    pub reverse_mapping: HashMap<String, String>,
    #[pyo3(get)]
    pub content_hash: String,
}

#[pymethods]
impl AnonymizationResult {
    #[new]
    pub fn new(
        text: String,
        mapping: HashMap<String, String>,
        reverse_mapping: HashMap<String, String>,
        content_hash: String,
    ) -> Self {
        Self {
            text,
            mapping,
            reverse_mapping,
            content_hash,
        }
    }
}

// Input structs for FromPyObject (used in function parameters)
// These accept ANY Python object with matching attribute names.
// Fields are read by the FromPyObject derive macro, not directly in Rust code.

#[derive(FromPyObject)]
#[allow(dead_code)]
pub struct SpeakerSegmentInput {
    pub speaker_id: String,
    pub start_time: f64,
    pub end_time: f64,
    pub confidence: Option<f64>,
}

#[derive(FromPyObject)]
#[allow(dead_code)]
pub struct WordTimingInput {
    pub word: String,
    pub start_time: f64,
    pub end_time: f64,
    pub confidence: Option<f64>,
}

#[derive(FromPyObject)]
#[allow(dead_code)]
pub struct SpeakerUtteranceInput {
    pub speaker_id: String,
    pub text: String,
    pub start_time: f64,
    pub end_time: f64,
    pub words: Vec<WordTimingInput>,
}

#[derive(FromPyObject)]
#[allow(dead_code)]
pub struct TranscriptionSpeakerSegmentInput {
    pub speaker_id: String,
    pub start_time: f64,
    pub end_time: f64,
    pub text: String,
}

// Output structs (returned from functions)

#[pyclass]
#[derive(Clone)]
pub struct SpeakerSegment {
    #[pyo3(get)]
    pub speaker_id: String,
    #[pyo3(get)]
    pub start_time: f64,
    #[pyo3(get)]
    pub end_time: f64,
    #[pyo3(get)]
    pub confidence: Option<f64>,
}

#[pymethods]
impl SpeakerSegment {
    #[new]
    #[pyo3(signature = (speaker_id, start_time, end_time, confidence=None))]
    pub fn new(
        speaker_id: String,
        start_time: f64,
        end_time: f64,
        confidence: Option<f64>,
    ) -> Self {
        Self {
            speaker_id,
            start_time,
            end_time,
            confidence,
        }
    }
}

#[pyclass]
#[derive(Clone)]
pub struct WordTiming {
    #[pyo3(get)]
    pub word: String,
    #[pyo3(get)]
    pub start_time: f64,
    #[pyo3(get)]
    pub end_time: f64,
    #[pyo3(get)]
    pub confidence: Option<f64>,
}

#[pymethods]
impl WordTiming {
    #[new]
    #[pyo3(signature = (word, start_time, end_time, confidence=None))]
    pub fn new(word: String, start_time: f64, end_time: f64, confidence: Option<f64>) -> Self {
        Self {
            word,
            start_time,
            end_time,
            confidence,
        }
    }
}

#[pyclass]
#[derive(Clone)]
pub struct SpeakerUtterance {
    #[pyo3(get)]
    pub speaker_id: String,
    #[pyo3(get)]
    pub text: String,
    #[pyo3(get)]
    pub start_time: f64,
    #[pyo3(get)]
    pub end_time: f64,
    #[pyo3(get)]
    pub words: Vec<WordTiming>,
}

#[pymethods]
impl SpeakerUtterance {
    #[new]
    pub fn new(
        speaker_id: String,
        text: String,
        start_time: f64,
        end_time: f64,
        words: Vec<WordTiming>,
    ) -> Self {
        Self {
            speaker_id,
            text,
            start_time,
            end_time,
            words,
        }
    }
}

#[pyclass]
#[derive(Clone)]
pub struct TranscriptionSpeakerSegment {
    #[pyo3(get)]
    pub speaker_id: String,
    #[pyo3(get)]
    pub start_time: f64,
    #[pyo3(get)]
    pub end_time: f64,
    #[pyo3(get)]
    pub text: String,
}

#[pymethods]
impl TranscriptionSpeakerSegment {
    #[new]
    pub fn new(speaker_id: String, start_time: f64, end_time: f64, text: String) -> Self {
        Self {
            speaker_id,
            start_time,
            end_time,
            text,
        }
    }
}
