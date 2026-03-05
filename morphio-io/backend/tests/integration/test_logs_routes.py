"""Purpose: Verify log-upload route behavior under realistic repeated usage.
Responsibilities: Ensure duplicate upload filenames do not collide on disk when jobs are enqueued.
Scope: Integration coverage for log-processing route file handling.
Usage: Executed by pytest in the backend integration suite.
Invariants/Assumptions: Multiple uploads with the same client filename must receive unique stored paths.
"""

import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient


async def _register_user(client: AsyncClient) -> str:
    response = await client.post(
        "/auth/register",
        json={
            "email": f"logs_route_{uuid.uuid4().hex[:8]}@example.com",
            "password": "StrongP@ssw0rd!",
            "display_name": "logs_route_user",
        },
    )
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_process_logs_uses_unique_storage_paths_for_duplicate_filenames(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    token = await _register_user(client)
    headers = {"Authorization": f"Bearer {token}"}
    captured_paths: list[str] = []

    from app.routes import logs as logs_routes

    monkeypatch.setattr(logs_routes.settings, "UPLOAD_DIR", str(tmp_path), raising=False)

    async def fake_enqueue(
        file_path: Path, user_id: int, db, model_name: str = "", anonymize: bool = False
    ) -> str:
        captured_paths.append(str(file_path))
        return f"job-{len(captured_paths)}"

    monkeypatch.setattr(logs_routes, "enqueue_logs_processing", fake_enqueue)

    files = {"log_file": ("duplicate.log", b"first line\n", "text/plain")}
    first = await client.post("/logs/process-logs", headers=headers, files=files)
    second = await client.post("/logs/process-logs", headers=headers, files=files)

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(captured_paths) == 2
    assert captured_paths[0] != captured_paths[1]
    assert captured_paths[0].endswith("duplicate.log")
    assert captured_paths[1].endswith("duplicate_1.log")
