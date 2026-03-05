"""Purpose: Exercise CSRF and browser-origin security boundaries.
Responsibilities: Verify refresh-token CSRF enforcement and local-dev origin handling.
Scope: Integration coverage for auth boundary middleware and rate limiting behavior.
Usage: Executed by pytest in the backend integration suite.
Invariants/Assumptions: Production keeps strict CSRF checks while non-production must support loopback origins on non-standard local ports.
"""

import uuid

import pytest
from httpx import AsyncClient

from app.config import settings


@pytest.mark.asyncio
async def test_refresh_token_csrf_flow(client: AsyncClient, monkeypatch):
    """Test CSRF token flow for refresh token endpoint."""
    # Force production for CSRF enforcement
    monkeypatch.setattr(settings, "APP_ENV", "production", raising=False)
    # Allow cookies over http in tests
    monkeypatch.setattr(settings, "DEBUG", True, raising=False)

    # Register user (no CSRF required for registration)
    reg = await client.post(
        "/auth/register",
        json={
            "email": f"csrf_user_{uuid.uuid4().hex[:8]}@example.com",
            "password": "StrongP@ssw0rd!",
            "display_name": "csrf_user",
        },
    )
    assert reg.status_code == 200

    # Get CSRF token BEFORE login (login now requires CSRF in production)
    csrf = await client.get("/auth/csrf-token")
    assert csrf.status_code == 200
    token = csrf.json()["data"]["csrf_token"]
    assert token
    client.cookies.set("csrf_token", token)

    # Login WITH CSRF token
    login = await client.post(
        "/auth/login",
        json={
            "email": reg.json()["data"]["user"]["email"],
            "password": "StrongP@ssw0rd!",
        },
        headers={"X-CSRF-Token": token},
    )
    assert login.status_code == 200

    # Get refresh token from cookies or create manually
    refresh_token_value = client.cookies.get("refresh_token")
    if not refresh_token_value:
        from app.services.security import create_refresh_token

        user_id = reg.json()["data"]["user"]["id"]
        refresh_token_value = create_refresh_token(data={"sub": str(user_id)})
        client.cookies.set("refresh_token", refresh_token_value)

    # Successful refresh with CSRF header present
    ok = await client.post("/auth/refresh-token", headers={"X-CSRF-Token": token})
    assert ok.status_code == 200

    # Get a new CSRF token (refresh rotates the token, so get a fresh one)
    csrf2 = await client.get("/auth/csrf-token")
    token2 = csrf2.json()["data"]["csrf_token"]
    client.cookies.set("csrf_token", token2)

    # Update refresh token cookie from the previous successful refresh
    new_refresh = client.cookies.get("refresh_token")
    if not new_refresh:
        # Create a new one for testing
        from app.services.security import create_refresh_token

        user_id = reg.json()["data"]["user"]["id"]
        new_refresh = create_refresh_token(data={"sub": str(user_id)})
        client.cookies.set("refresh_token", new_refresh)

    # Missing CSRF header -> 403 in production
    fail = await client.post("/auth/refresh-token")
    assert fail.status_code == 403


@pytest.mark.asyncio
async def test_rate_limit_exceeded(client: AsyncClient, monkeypatch):
    """Test that rate limiting returns 429 status."""
    from slowapi.errors import RateLimitExceeded

    from app.utils import decorators

    # Create a mock Limit object
    class MockLimit:
        def __init__(self):
            self.limit = "60/minute"
            self.error_message = "Rate limit exceeded: 60/minute"

        def __str__(self):
            return self.limit

    # Create a proper RateLimitExceeded exception
    class MockRateLimitExceeded(RateLimitExceeded):
        def __init__(self, limit_value: str | MockLimit):
            # Create a mock limit object if limit is a string
            if isinstance(limit_value, str):
                mock_limit = MockLimit()
                mock_limit.limit = limit_value
                mock_limit.error_message = f"Rate limit exceeded: {limit_value}"
                limit_value = mock_limit
            self.limit = limit_value
            self.retry_after = 60
            # Skip super().__init__ as we're mocking - we just need .limit and .retry_after
            Exception.__init__(self, str(limit_value))

    # Monkeypatch the module-level _ratelimit_func to raise RateLimitExceeded
    async def fake_ratelimit(request, limit):
        raise MockRateLimitExceeded(limit)

    monkeypatch.setattr(decorators, "_ratelimit_func", fake_ratelimit)
    # Also ensure rate limiting is enabled
    monkeypatch.setattr("app.config.settings.RATE_LIMITING_ENABLED", True, raising=False)

    resp = await client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "bad"},
    )
    assert resp.status_code == 429, f"Expected 429, got {resp.status_code}. Response: {resp.json()}"


@pytest.mark.asyncio
async def test_non_standard_local_origin_preflight_is_allowed_in_dev(
    client: AsyncClient, monkeypatch
):
    monkeypatch.setattr(settings, "APP_ENV", "development", raising=False)

    response = await client.options(
        "/auth/login",
        headers={
            "Origin": "http://127.0.0.1:3015",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3015"
