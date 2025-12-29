"""
Integration test for persisted stage progress updates (no Redis).

This test verifies that when processing a log file:
1. Stage transitions are tracked correctly
2. The final status is accessible via the API
3. Stages progress in order: downloading -> generating -> saving -> completed
"""

import asyncio
import uuid
from pathlib import Path

import pytest

from app.config import settings


# In-memory cache to track stage transitions
_in_memory_cache: dict = {}
_stage_transitions: list = []


async def _mock_get_cache(key: str):
    """Mock get_cache that returns from in-memory dict."""
    return _in_memory_cache.get(key)


async def _mock_set_cache(key: str, value, expire: int = 3600):
    """Mock set_cache that stores in in-memory dict and tracks stages."""
    import json

    _in_memory_cache[key] = json.dumps(value) if not isinstance(value, str) else value

    # Track stage transitions from job status updates
    if "media" in key and isinstance(value, dict):
        stage = value.get("stage")
        if stage and (not _stage_transitions or _stage_transitions[-1] != stage):
            _stage_transitions.append(stage)
    return True


async def _register_user(async_client):
    """Register a new test user and return the access token."""
    user_data = {
        "email": f"stage-test-{uuid.uuid4()}@example.com",
        "password": "StrongP@ssw0rd123!",
        "display_name": "Stage Tester",
    }
    response = await async_client.post("/auth/register", json=user_data)
    assert response.status_code == 200, response.json()
    return response.json()["data"]["access_token"]


@pytest.fixture(autouse=True)
def reset_in_memory_cache():
    """Reset in-memory cache before each test."""
    global _in_memory_cache, _stage_transitions
    _in_memory_cache = {}
    _stage_transitions = []
    yield
    _in_memory_cache = {}
    _stage_transitions = []


class TestLogsStageProgressUpdates:
    """Test stage progress updates during log processing."""

    async def test_stage_transitions_during_log_processing(
        self, async_client, db_session, monkeypatch, tmp_path
    ):
        """
        Test that processing a log file goes through correct stage transitions.

        Flow:
        1. Register user, get bearer token
        2. POST /logs/process-logs with a small log file -> capture job_id
        3. Poll GET /logs/logs-processing-status/{job_id} until status=="completed"
        4. Assert the persisted stage transitions contain, in order:
           downloading -> generating -> saving -> completed
        """
        # Monkeypatch cache functions to use in-memory storage
        monkeypatch.setattr(
            "app.utils.cache_utils.get_cache",
            _mock_get_cache,
        )
        monkeypatch.setattr(
            "app.utils.cache_utils.set_cache",
            _mock_set_cache,
        )
        # Also patch in job status module which imports from cache_utils
        monkeypatch.setattr(
            "app.services.job.status.get_cache",
            _mock_get_cache,
        )
        monkeypatch.setattr(
            "app.services.job.status.set_cache",
            _mock_set_cache,
        )

        # Mock the heavy processing functions to make the test fast
        async def mock_load_template(template_id, db):
            return "Test template: summarize {transcript}"

        async def mock_generate_content(transcript, template_content, chosen_model):
            return {"content": "Generated summary", "title": "Test Summary"}

        async def mock_save_content(content_dict, user_id):
            from unittest.mock import MagicMock

            mock_content = MagicMock()
            mock_content.id = 1
            # content_dict can be either a dict or string (from deanonymize_content)
            if isinstance(content_dict, dict):
                mock_content.content = content_dict.get("content", "")
                mock_content.title = content_dict.get("title", "")
            else:
                mock_content.content = str(content_dict)
                mock_content.title = "Generated Content"
            return mock_content

        async def mock_increment_usage(db, user_id, usage_type):
            pass

        async def mock_get_cached_content(*args, **kwargs):
            return None

        async def mock_cache_content(*args, **kwargs):
            pass

        monkeypatch.setattr(
            "app.services.logs.processing.load_template",
            mock_load_template,
        )
        monkeypatch.setattr(
            "app.services.logs.processing.generate_content_from_transcript",
            mock_generate_content,
        )
        monkeypatch.setattr(
            "app.services.logs.processing.save_generated_content",
            mock_save_content,
        )
        monkeypatch.setattr(
            "app.services.logs.processing.increment_usage",
            mock_increment_usage,
        )
        monkeypatch.setattr(
            "app.services.logs.processing.get_cached_generated_content",
            mock_get_cached_content,
        )
        monkeypatch.setattr(
            "app.services.logs.processing.cache_generated_content",
            mock_cache_content,
        )

        # Step 1: Register user
        access_token = await _register_user(async_client)
        headers = {"Authorization": f"Bearer {access_token}"}

        # Step 2: Create a small test log file and upload it
        # Use a temporary file path that the processing will use
        log_content = "2025-01-01 INFO Test log entry\n2025-01-01 DEBUG Another entry\n"
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)

        files = {"log_file": ("test.log", log_content.encode(), "text/plain")}
        response = await async_client.post(
            "/logs/process-logs",
            files=files,
            headers=headers,
        )

        assert response.status_code == 200, response.json()
        job_id = response.json()["data"]["job_id"]
        assert job_id is not None

        # Step 3: Poll for completion with timeout
        max_attempts = 50
        poll_interval = 0.1  # 100ms
        final_status = None

        for _ in range(max_attempts):
            status_response = await async_client.get(
                f"/logs/logs-processing-status/{job_id}",
                headers=headers,
            )
            assert status_response.status_code == 200

            status_data = status_response.json()["data"]
            final_status = status_data["status"]

            if final_status in ("completed", "failed"):
                break

            await asyncio.sleep(poll_interval)

        # Step 4: Assert completion and stage transitions
        assert final_status == "completed", f"Job did not complete. Final status: {final_status}"

        # Verify stage transitions happened in correct order
        # The expected flow is: downloading -> generating -> saving -> completed
        expected_stages = ["downloading", "generating", "saving", "completed"]

        # Filter to only the expected stages (there may be duplicates)
        observed_stages = []
        for stage in _stage_transitions:
            if stage in expected_stages and (not observed_stages or observed_stages[-1] != stage):
                observed_stages.append(stage)

        # Verify the stages appear in the correct order
        stage_indices = {stage: i for i, stage in enumerate(expected_stages)}
        for i, stage in enumerate(observed_stages[:-1]):
            next_stage = observed_stages[i + 1]
            assert stage_indices.get(stage, -1) < stage_indices.get(next_stage, -1), (
                f"Stage order violation: {stage} should come before {next_stage}. "
                f"Observed transitions: {_stage_transitions}"
            )

        # Verify all expected stages were hit
        for stage in expected_stages:
            assert stage in _stage_transitions, (
                f"Expected stage '{stage}' not found in transitions: {_stage_transitions}"
            )
