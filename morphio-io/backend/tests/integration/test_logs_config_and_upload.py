import uuid

import pytest

from app.config import settings


async def _register_user(async_client):
    user_data = {
        "email": f"user-{uuid.uuid4()}@example.com",
        "password": "StrongP@ssw0rd123!",
        "display_name": "Log Tester",
    }
    response = await async_client.post("/auth/register", json=user_data)
    assert response.status_code == 200, response.json()
    return response.json()["data"]["access_token"]


async def test_log_config_includes_max_upload_size(async_client):
    response = await async_client.get("/logs/config")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert "allowed_extensions" in payload["data"]
    assert payload["data"]["max_upload_size"] == settings.MAX_UPLOAD_SIZE


@pytest.mark.parametrize(
    "endpoint",
    ["/logs/process-logs", "/logs/generate-splunk-config"],
)
async def test_log_upload_rejects_oversized_files(async_client, monkeypatch, endpoint):
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE", 5)
    access_token = await _register_user(async_client)
    headers = {"Authorization": f"Bearer {access_token}"}
    files = {"log_file": ("oversize.log", b"123456", "text/plain")}

    response = await async_client.post(endpoint, files=files, headers=headers)

    assert response.status_code == 413
