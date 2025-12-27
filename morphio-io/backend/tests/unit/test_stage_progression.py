from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.logs.processing import process_logs_file
from app.utils.enums import ProcessingStage


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
