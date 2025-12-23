"""Tests for LLM usage tracking.

These tests verify that LLMUsageRecord entries are correctly created
and that token counts are accurately stored for billing/analytics.
"""

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_usage import LLMUsageRecord
from app.models.user import User
from app.services.usage.tracking import record_llm_usage
from app.utils.enums import UserRole
from app.utils.response_utils import utc_now


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        email="llm_test@example.com",
        hashed_password="test_hash",
        display_name="LLM Test User",
        role=UserRole.USER,
        created_at=utc_now(),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestRecordLLMUsage:
    """Tests for record_llm_usage function."""

    async def test_creates_usage_record(self, db_session: AsyncSession, test_user: User):
        """record_llm_usage should create an LLMUsageRecord."""
        record = await record_llm_usage(
            db_session,
            user_id=test_user.id,
            provider="openai",
            model="gpt-4o",
            input_tokens=100,
            output_tokens=50,
        )

        assert record.id is not None
        assert record.user_id == test_user.id
        assert record.provider == "openai"
        assert record.model == "gpt-4o"
        assert record.input_tokens == 100
        assert record.output_tokens == 50
        assert record.total_tokens == 150

    async def test_stores_token_counts_accurately(self, db_session: AsyncSession, test_user: User):
        """Token counts should be accurately stored in the database."""
        await record_llm_usage(
            db_session,
            user_id=test_user.id,
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_tokens=1234,
            output_tokens=5678,
        )

        # Verify from database
        result = await db_session.execute(
            select(LLMUsageRecord).where(LLMUsageRecord.user_id == test_user.id)
        )
        record = result.unique().scalar_one()

        assert record.input_tokens == 1234
        assert record.output_tokens == 5678
        assert record.total_tokens == 1234 + 5678

    async def test_stores_model_alias(self, db_session: AsyncSession, test_user: User):
        """Model alias should be stored separately from actual model."""
        record = await record_llm_usage(
            db_session,
            user_id=test_user.id,
            provider="openai",
            model="gpt-4o-2025-01-01",
            model_alias="gpt-5-high",
            input_tokens=100,
            output_tokens=50,
        )

        assert record.model == "gpt-4o-2025-01-01"  # Actual model
        assert record.model_alias == "gpt-5-high"  # User-facing alias

    async def test_stores_cost_estimate(self, db_session: AsyncSession, test_user: User):
        """Cost estimate should be stored when provided."""
        record = await record_llm_usage(
            db_session,
            user_id=test_user.id,
            provider="openai",
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=Decimal("0.0045"),
        )

        assert record.cost_usd == Decimal("0.0045")

    async def test_stores_operation_type(self, db_session: AsyncSession, test_user: User):
        """Operation type should be stored for analytics."""
        record = await record_llm_usage(
            db_session,
            user_id=test_user.id,
            provider="gemini",
            model="gemini-3-flash",
            input_tokens=200,
            output_tokens=100,
            operation="content_generation",
        )

        assert record.operation == "content_generation"

    async def test_stores_content_id_reference(self, db_session: AsyncSession, test_user: User):
        """Content ID reference should be stored when provided."""
        record = await record_llm_usage(
            db_session,
            user_id=test_user.id,
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_tokens=100,
            output_tokens=50,
            content_id=42,
        )

        assert record.content_id == 42

    async def test_multiple_records_per_user(self, db_session: AsyncSession, test_user: User):
        """Multiple LLM usage records can be created for the same user."""
        # Create multiple records
        await record_llm_usage(
            db_session,
            user_id=test_user.id,
            provider="openai",
            model="gpt-4o",
            input_tokens=100,
            output_tokens=50,
        )
        await record_llm_usage(
            db_session,
            user_id=test_user.id,
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_tokens=200,
            output_tokens=100,
        )
        await record_llm_usage(
            db_session,
            user_id=test_user.id,
            provider="gemini",
            model="gemini-3-flash",
            input_tokens=300,
            output_tokens=150,
        )

        # Verify all three exist
        result = await db_session.execute(
            select(LLMUsageRecord).where(LLMUsageRecord.user_id == test_user.id)
        )
        records = result.unique().scalars().all()

        assert len(records) == 3
        providers = {r.provider for r in records}
        assert providers == {"openai", "anthropic", "gemini"}
