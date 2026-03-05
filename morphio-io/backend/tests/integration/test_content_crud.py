"""Purpose: Verify user-facing content CRUD behavior.
Responsibilities: Exercise create/update/delete flows, including tag persistence on content edits.
Scope: Integration coverage for authenticated content routes and ORM relationship handling.
Usage: Executed by pytest in the backend integration suite.
Invariants/Assumptions: String tag payloads from API clients must round-trip without database errors.
"""

import uuid

import pytest
from httpx import AsyncClient


async def _register_user(client: AsyncClient) -> str:
    response = await client.post(
        "/auth/register",
        json={
            "email": f"content_crud_{uuid.uuid4().hex[:8]}@example.com",
            "password": "StrongP@ssw0rd!",
            "display_name": "content_crud_user",
        },
    )
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_content_update_persists_tag_names_without_database_error(client: AsyncClient):
    token = await _register_user(client)
    headers = {"Authorization": f"Bearer {token}"}

    created = await client.post(
        "/content/save-content",
        json={
            "title": "Initial title",
            "content": "Initial body",
            "tags": ["alpha", "beta"],
        },
        headers=headers,
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["data"]["tags"] == ["alpha", "beta"]
    content_id = payload["data"]["id"]

    updated = await client.put(
        f"/content/update-content/{content_id}",
        json={
            "title": "Updated title",
            "content": "Updated body",
            "tags": ["beta", "gamma"],
        },
        headers=headers,
    )
    assert updated.status_code == 200
    updated_payload = updated.json()
    assert updated_payload["data"]["title"] == "Updated title"
    assert updated_payload["data"]["content"] == "Updated body"
    assert updated_payload["data"]["tags"] == ["beta", "gamma"]
