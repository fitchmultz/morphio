from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.media_schema import MediaProcessingInput
from app.services.audio.processing import transcribe_and_generate_audio
from app.services.logs.processing import process_logs_file
from app.utils.enums import MediaSource, MediaType, ProcessingStage


@pytest.mark.asyncio
async def test_logs_processing_emits_stage_progression(tmp_path):
    log_path = tmp_path / "sample.log"
    log_path.write_text("INFO sample log entry\n", encoding="utf-8")

    mock_db = AsyncMock()
    mock_job_status = SimpleNamespace(chosen_model="test-model")
    mock_update_job_status = AsyncMock()
    mock_generate_content = AsyncMock(return_value="generated summary")
    mock_save_generated_content = AsyncMock(
        return_value=SimpleNamespace(content="generated summary", title="Title", id=1)
    )

    def _noop_anonymize(content: str, _anonymize: bool) -> str:
        return content

    def _noop_deanonymize(content: str, _processed_logs: str, _anonymize: bool) -> str:
        return content

    with (
        patch(
            "app.services.logs.processing.get_job_status",
            AsyncMock(return_value=mock_job_status),
        ),
        patch("app.services.logs.processing.update_job_status", mock_update_job_status),
        patch("app.services.logs.processing.increment_usage", AsyncMock()),
        patch("app.services.logs.processing.compute_file_hash", AsyncMock(return_value="hash")),
        patch("app.services.logs.processing.load_template", AsyncMock(return_value="template")),
        patch(
            "app.services.logs.processing.get_cached_generated_content",
            AsyncMock(return_value=None),
        ),
        patch(
            "app.services.logs.processing.generate_content_from_transcript",
            mock_generate_content,
        ),
        patch("app.services.logs.processing.cache_generated_content", AsyncMock()),
        patch("app.services.logs.processing.save_generated_content", mock_save_generated_content),
        patch("app.services.logs.processing.anonymize_content", _noop_anonymize),
        patch("app.services.logs.processing.deanonymize_content", _noop_deanonymize),
    ):
        await process_logs_file(
            {"file_path": str(log_path), "anonymize": False},
            "job-123",
            mock_db,
            1,
        )

    stages = [
        call.kwargs.get("stage")
        for call in mock_update_job_status.call_args_list
        if call.kwargs.get("stage") is not None
    ]

    expected = [
        ProcessingStage.DOWNLOADING,
        ProcessingStage.GENERATING,
        ProcessingStage.SAVING,
        ProcessingStage.COMPLETED,
    ]

    matched = 0
    for stage in stages:
        if stage == expected[matched]:
            matched += 1
            if matched == len(expected):
                break

    assert matched == len(expected), f"Expected stages {expected}, got {stages}"


@pytest.mark.asyncio
async def test_audio_processing_emits_stage_progression(tmp_path):
    audio_path = tmp_path / "sample.wav"
    audio_path.write_text("dummy audio data", encoding="utf-8")

    input_data = MediaProcessingInput(
        source=MediaSource.UPLOAD,
        file_path=str(audio_path),
        template_id=0,
        user_id=1,
        media_type=MediaType.AUDIO,
        enable_diarization=False,
    )

    mock_db = AsyncMock()
    mock_job_status = SimpleNamespace(chosen_model="test-model")
    mock_update_job_status = AsyncMock()
    chunk_result = SimpleNamespace(chunks=[SimpleNamespace(chunk_path="chunk1.wav")])

    with (
        patch(
            "app.services.audio.processing.get_job_status",
            AsyncMock(return_value=mock_job_status),
        ),
        patch("app.services.audio.processing.update_job_status", mock_update_job_status),
        patch("app.services.audio.pipeline.update_job_status", mock_update_job_status),
        patch("app.services.audio.processing.increment_usage", AsyncMock()),
        patch("app.services.audio.processing.compute_file_hash", AsyncMock(return_value="hash")),
        patch(
            "app.services.audio.processing.get_cached_whisper_transcription",
            AsyncMock(return_value=None),
        ),
        patch("app.services.audio.processing.cache_whisper_transcription", AsyncMock()),
        patch(
            "app.services.audio.processing.chunk_audio_file", AsyncMock(return_value=chunk_result)
        ),
        patch("app.services.audio.processing.cleanup_chunks", AsyncMock()),
        patch(
            "app.services.audio.pipeline.transcribe_audio_chunk", AsyncMock(return_value="hello")
        ),
    ):
        await transcribe_and_generate_audio(input_data, "job-123", mock_db, 1)

    stages = [
        call.kwargs.get("stage")
        for call in mock_update_job_status.call_args_list
        if call.kwargs.get("stage") is not None
    ]

    expected = [
        ProcessingStage.QUEUED,
        ProcessingStage.DOWNLOADING,
        ProcessingStage.CHUNKING,
        ProcessingStage.TRANSCRIBING,
        ProcessingStage.GENERATING,
        ProcessingStage.COMPLETED,
    ]

    matched = 0
    for stage in stages:
        if stage == expected[matched]:
            matched += 1
            if matched == len(expected):
                break

    assert matched == len(expected), f"Expected stages {expected}, got {stages}"
