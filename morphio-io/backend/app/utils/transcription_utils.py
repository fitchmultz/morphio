import json
import re

from .types import TranscriptionLike


def clean_transcription(transcript: str) -> str:
    """Clean transcription by removing placeholders and filler words."""
    if not isinstance(transcript, str):
        raise ValueError("Transcription must be a string.")
    cleaned = re.sub(r"\[(?:MUSIC|inaudible)\]", "", transcript)
    filler_words = ["um", "uh", "ah"]
    cleaned = re.sub(r"\b(?:{})\b".format("|".join(filler_words)), "", cleaned)
    return cleaned.strip()


def serialize_transcription(transcription: TranscriptionLike) -> str:
    """Serialize transcription to JSON string for caching."""
    if isinstance(transcription, str):
        return json.dumps({"text": transcription})
    elif hasattr(transcription, "__dict__"):
        return json.dumps(transcription.__dict__)
    return json.dumps({"text": str(transcription)})
