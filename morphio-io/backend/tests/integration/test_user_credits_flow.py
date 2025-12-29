"""
API E2E tests for the user credits flow.

Tests the GET /user/credits endpoint to verify:
1. New user gets correct defaults (free plan, full credits)
2. Usage rows are reflected in credits
3. Subscription plan changes update limits
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.config import settings
from app.models.subscription import Subscription
from app.models.usage import Usage
from app.models.user import User


async def _register_user(async_client):
    """Register a new test user and return the access token."""
    user_data = {
        "email": f"credits-test-{uuid.uuid4()}@example.com",
        "password": "StrongP@ssw0rd123!",
        "display_name": "Credits Tester",
    }
    response = await async_client.post("/auth/register", json=user_data)
    assert response.status_code == 200, response.json()
    return response.json()["data"]["access_token"]


async def _get_user_id_from_token(async_client, access_token, db_session):
    """Get user ID by making a profile request and looking up in DB."""
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await async_client.get("/user/profile", headers=headers)
    assert response.status_code == 200
    email = response.json()["data"]["email"]
    result = await db_session.execute(select(User).where(User.email == email))
    user = result.scalar_one()
    return user.id


class TestCreditsFlowNewUser:
    """Test 1: New user gets correct default credits."""

    async def test_new_user_gets_default_credits(self, async_client):
        """Register a new user and verify GET /user/credits returns correct defaults."""
        access_token = await _register_user(async_client)
        headers = {"Authorization": f"Bearer {access_token}"}

        response = await async_client.get("/user/credits", headers=headers)

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "success"

        data = payload["data"]
        free_limit = settings.SUBSCRIPTION_PLAN_LIMITS["free"]

        assert data["plan"] == "free"
        assert data["limit"] == free_limit
        assert data["used"] == 0
        assert data["remaining"] == free_limit
        assert data["remaining_pct"] == 100.0
        assert data["resets_monthly"] is True

        # reset_date should be YYYY-MM-01 format for next month
        reset_date = data["reset_date"]
        assert len(reset_date) == 10
        assert reset_date.endswith("-01")


class TestCreditsFlowWithUsage:
    """Test 2: Usage rows are reflected in credits."""

    async def test_usage_reflected_in_credits(self, async_client, db_session):
        """Insert a Usage row for the user and verify credits reflect it."""
        access_token = await _register_user(async_client)
        headers = {"Authorization": f"Bearer {access_token}"}
        user_id = await _get_user_id_from_token(async_client, access_token, db_session)

        # Insert a usage row for current month
        now = datetime.now(timezone.utc)
        usage = Usage(
            user_id=user_id,
            usage_type="log_processing",
            usage_count=5,
            usage_credits=10,
            created_at=now,
            updated_at=now,
        )
        db_session.add(usage)
        await db_session.commit()

        response = await async_client.get("/user/credits", headers=headers)

        assert response.status_code == 200
        data = response.json()["data"]
        free_limit = settings.SUBSCRIPTION_PLAN_LIMITS["free"]

        assert data["used"] == 10
        assert data["remaining"] == free_limit - 10
        expected_pct = round(((free_limit - 10) / free_limit) * 100, 1)
        assert data["remaining_pct"] == expected_pct


class TestCreditsFlowWithSubscription:
    """Test 3: Active subscription updates plan and limits."""

    async def test_pro_subscription_updates_credits(self, async_client, db_session):
        """Insert an active Subscription(plan='pro') and verify credits reflect it."""
        access_token = await _register_user(async_client)
        headers = {"Authorization": f"Bearer {access_token}"}
        user_id = await _get_user_id_from_token(async_client, access_token, db_session)

        # Insert an active pro subscription
        subscription = Subscription(
            user_id=user_id,
            plan="pro",
            status="active",
        )
        db_session.add(subscription)
        await db_session.commit()

        response = await async_client.get("/user/credits", headers=headers)

        assert response.status_code == 200
        data = response.json()["data"]
        pro_limit = settings.SUBSCRIPTION_PLAN_LIMITS["pro"]

        assert data["plan"] == "pro"
        assert data["limit"] == pro_limit
        assert data["used"] == 0
        assert data["remaining"] == pro_limit
