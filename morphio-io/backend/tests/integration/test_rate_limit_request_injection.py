"""
Purpose: Guard against regressions where rate-limited FastAPI routes fail to receive Request.
Responsibilities: Validate that a representative rate-limited endpoint executes with rate limiting enabled.
Scope: Integration coverage for /template/get-templates with auth override and mocked rate limiter.
Usage: Executed by pytest in backend integration suite.
Invariants/Assumptions: RATE_LIMITING_ENABLED can be toggled via settings monkeypatch in tests.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import Request

from app.config import settings
from app.main import app
from app.models.user import User
from app.services.security import get_current_user
from app.utils import decorators


@pytest.mark.asyncio
async def test_rate_limited_template_endpoint_receives_request(client, monkeypatch):
    """Ensure rate-limited routes receive Request and do not 500 from decorator fallback."""

    monkeypatch.setattr(settings, "RATE_LIMITING_ENABLED", True)

    ratelimit_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(decorators, "_ratelimit_func", ratelimit_mock)

    monkeypatch.setattr(
        "app.routes.template.get_all_templates",
        AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "name": "Default Template",
                    "template_content": "Summary: {transcript}",
                    "is_default": True,
                    "user_id": None,
                    "created_at": datetime.now(UTC),
                }
            ]
        ),
    )

    user = User(
        id=1,
        email="rate-limit-test@example.com",
        hashed_password="hashed-password",
        display_name="Rate Limit Test User",
    )

    async def override_current_user():
        return user

    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = await client.get("/template/get-templates")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    ratelimit_mock.assert_awaited_once()
    await_args = ratelimit_mock.await_args
    assert await_args is not None
    request_arg = await_args.args[0]
    assert isinstance(request_arg, Request)
