import logging
import os
from unittest.mock import patch

import pytest
from app.schemas.audio_schema import TranscriptionResult
from app.services.audio import transcribe_audio
from app.services.video import process_local_video

# Check if a whisper backend is available
_whisper_available = False
try:
    from morphio_core.audio import detect_optimal_backend

    _whisper_available = detect_optimal_backend() is not None
except Exception:
    pass

pytestmark = pytest.mark.skipif(not _whisper_available, reason="Whisper backend not installed")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use the test video file from test_files directory (project root)
# This is Charlie Chaplin's "The Great Dictator" final speech
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
TEST_VIDEO_FILE = os.path.join(
    PROJECT_ROOT,
    "test_files",
    "YTDown.com_YouTube_Charlie-Chaplin-Final-Speech-from-The-Gr_Media_J7GY1Xg6X20_001_1080p.mp4",
)
# For audio tests, we use the same video file (audio will be extracted)
TEST_AUDIO_FILE = TEST_VIDEO_FILE

# Expected words/phrases from Charlie Chaplin's "The Great Dictator" speech
CHAPLIN_SPEECH_KEYWORDS = [
    "emperor",
    "humanity",
    "soldiers",
    "liberty",
    "democracy",
    "greed",
    "machine",
]


@pytest.fixture(autouse=True)
def mock_update_job_status():
    """Mock the update_job_status function to avoid Redis dependency"""
    with patch("app.services.job.update_job_status") as mock:
        mock.return_value = None
        yield mock


@pytest.mark.asyncio
@pytest.mark.timeout(120)  # Allow up to 2 minutes for real transcription
async def test_transcribe_audio_with_real_transcription():
    """Test real audio transcription using the Charlie Chaplin speech video."""
    if not os.path.exists(TEST_AUDIO_FILE):
        pytest.skip(f"Test audio file not found: {TEST_AUDIO_FILE}")

    # Run actual transcription
    result = await transcribe_audio(TEST_AUDIO_FILE)

    # Assert that the result is a TranscriptionResult
    assert isinstance(result, TranscriptionResult)
    assert result.text, "Transcription should not be empty"

    # Verify the transcription contains expected keywords from Chaplin's speech
    text_lower = result.text.lower()
    found_keywords = [kw for kw in CHAPLIN_SPEECH_KEYWORDS if kw in text_lower]
    assert len(found_keywords) >= 3, (
        f"Expected at least 3 keywords from Chaplin's speech, found: {found_keywords}"
    )
    logger.info(f"Found keywords: {found_keywords}")


@pytest.mark.asyncio
async def test_transcribe_audio_file_not_found():
    """Test that transcribing a non-existent file returns empty result."""
    non_existent_file = "non_existent_audio.mp3"
    result = await transcribe_audio(non_existent_file)

    assert isinstance(result, TranscriptionResult)
    assert result.text == ""


@pytest.mark.asyncio
async def test_transcribe_audio_exception_handling():
    """Test that exceptions during transcription are handled gracefully."""
    if not os.path.exists(TEST_AUDIO_FILE):
        pytest.skip(f"Test audio file not found: {TEST_AUDIO_FILE}")

    # Mock the local transcription to raise an exception
    with patch("app.services.audio.transcription.transcribe_audio_local") as mock_transcribe_local:
        mock_transcribe_local.side_effect = Exception("Simulated transcription error")
        result = await transcribe_audio(TEST_AUDIO_FILE)

    # Should handle exception gracefully and return empty result
    assert isinstance(result, TranscriptionResult)
    assert result.text == ""


@pytest.mark.asyncio
@pytest.mark.timeout(180)  # Allow up to 3 minutes for video processing
async def test_full_video_processing_flow():
    """Test the full video processing pipeline with real transcription."""
    if not os.path.exists(TEST_VIDEO_FILE):
        pytest.skip(f"Test video file not found: {TEST_VIDEO_FILE}")

    upload_dir = os.path.dirname(TEST_VIDEO_FILE)
    job_id = "test_job_id"

    # Mock update_job_status to avoid Redis dependency
    with patch("app.services.job.update_job_status"):
        transcription = await process_local_video(TEST_VIDEO_FILE, upload_dir, job_id)

    # Assert that the transcription is not empty
    assert transcription, "Transcription should not be empty"

    # Verify transcription contains expected content from Chaplin's speech
    text_lower = transcription.lower()
    found_keywords = [kw for kw in CHAPLIN_SPEECH_KEYWORDS if kw in text_lower]
    assert len(found_keywords) >= 3, (
        f"Expected at least 3 keywords from Chaplin's speech, found: {found_keywords}"
    )
