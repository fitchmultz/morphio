"""Tests for credits gating / usage limit enforcement.

These tests verify that the usage limit check (check_usage_limit) properly
blocks operations BEFORE expensive LLM calls when credits are exhausted.

This is a critical billing protection - users should not be able to exceed
their plan limits.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.models.usage import Usage
from app.models.user import User
from app.services.usage.tracking import check_usage_limit, increment_usage
from app.utils.enums import UsageType, UserRole
from app.utils.error_handlers import ApplicationException
from app.utils.response_utils import utc_now


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user with default free plan."""
    user = User(
        email="test@example.com",
        hashed_password="test_hash",
        display_name="Test User",
        role=UserRole.USER,
        created_at=utc_now(),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin user (should bypass all limits)."""
    user = User(
        email="admin@example.com",
        hashed_password="admin_hash",
        display_name="Admin User",
        role=UserRole.ADMIN,
        created_at=utc_now(),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def pro_user(db_session: AsyncSession) -> User:
    """Create a pro user with active subscription."""
    user = User(
        email="pro@example.com",
        hashed_password="pro_hash",
        display_name="Pro User",
        role=UserRole.USER,
        created_at=utc_now(),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Add active pro subscription
    subscription = Subscription(
        user_id=user.id,
        plan="pro",
        status="active",
        created_at=utc_now(),
    )
    db_session.add(subscription)
    await db_session.commit()

    return user


class TestCheckUsageLimit:
    """Tests for check_usage_limit function."""

    async def test_check_limit_passes_for_new_user(self, db_session: AsyncSession, test_user: User):
        """New user with no usage should pass the check."""
        result = await check_usage_limit(db_session, test_user.id, UsageType.OTHER)
        assert result is True

    async def test_check_limit_fails_when_exceeded(self, db_session: AsyncSession, test_user: User):
        """User at/over limit should be blocked with 403."""
        # Create usage that hits the limit (free plan = 50 credits)
        usage = Usage(
            user_id=test_user.id,
            usage_type=UsageType.OTHER.value,
            usage_count=50,
            usage_credits=50,  # At limit
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db_session.add(usage)
        await db_session.commit()

        # Should raise 403 ApplicationException
        with pytest.raises(ApplicationException) as exc_info:
            await check_usage_limit(db_session, test_user.id, UsageType.OTHER)

        assert exc_info.value.status_code == 403
        assert "credit limit" in exc_info.value.message.lower()

    async def test_admin_bypasses_limit(self, db_session: AsyncSession, admin_user: User):
        """Admin users should always pass, even with high usage."""
        # Create high usage for admin
        usage = Usage(
            user_id=admin_user.id,
            usage_type=UsageType.OTHER.value,
            usage_count=1000,
            usage_credits=1000,  # Way over free limit
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db_session.add(usage)
        await db_session.commit()

        # Admin should still pass
        result = await check_usage_limit(db_session, admin_user.id, UsageType.OTHER)
        assert result is True

    async def test_pro_user_has_higher_limit(self, db_session: AsyncSession, pro_user: User):
        """Pro users should have access to higher limits (1000 credits)."""
        # Create usage that would fail free limit but pass pro limit
        usage = Usage(
            user_id=pro_user.id,
            usage_type=UsageType.OTHER.value,
            usage_count=100,
            usage_credits=100,  # Over free limit (50), under pro limit (1000)
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db_session.add(usage)
        await db_session.commit()

        # Pro user should pass
        result = await check_usage_limit(db_session, pro_user.id, UsageType.OTHER)
        assert result is True

    async def test_user_not_found_raises_404(self, db_session: AsyncSession):
        """Checking non-existent user should raise 404."""
        with pytest.raises(ApplicationException) as exc_info:
            await check_usage_limit(db_session, 99999, UsageType.OTHER)

        assert exc_info.value.status_code == 404


class TestIncrementUsage:
    """Tests for increment_usage function."""

    async def test_increment_creates_usage_record(self, db_session: AsyncSession, test_user: User):
        """First increment should create a new Usage record."""
        await increment_usage(db_session, test_user.id, UsageType.OTHER)

        # Verify record created
        from sqlalchemy import select

        result = await db_session.execute(select(Usage).where(Usage.user_id == test_user.id))
        usage = result.scalar_one()
        assert usage.usage_count == 1
        assert usage.usage_credits >= 1

    async def test_increment_fails_at_limit(self, db_session: AsyncSession, test_user: User):
        """Increment should fail with 403 when limit reached."""
        # Set up user at limit
        usage = Usage(
            user_id=test_user.id,
            usage_type=UsageType.OTHER.value,
            usage_count=50,
            usage_credits=50,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db_session.add(usage)
        await db_session.commit()

        # Should fail to increment
        with pytest.raises(ApplicationException) as exc_info:
            await increment_usage(db_session, test_user.id, UsageType.OTHER)

        assert exc_info.value.status_code == 403

    async def test_weighted_usage_costs_apply(self, db_session: AsyncSession, test_user: User):
        """Video processing should cost 2 credits (based on USAGE_WEIGHTS)."""
        await increment_usage(db_session, test_user.id, UsageType.VIDEO_PROCESSING)

        from sqlalchemy import select

        result = await db_session.execute(
            select(Usage).where(
                Usage.user_id == test_user.id,
                Usage.usage_type == UsageType.VIDEO_PROCESSING.value,
            )
        )
        usage = result.scalar_one()
        assert usage.usage_count == 1
        assert usage.usage_credits == 2  # Video = 2 credits
