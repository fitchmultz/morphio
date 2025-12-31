from datetime import UTC, datetime
from unittest.mock import AsyncMock

from app.services.usage.tracking import get_current_period_usage_credits


class _NoRowResult:
    def __init__(self, value: int):
        self._value = value

    def scalar_one(self):
        return self._value

    def scalars(self):
        raise AssertionError("Aggregate query should not materialize ORM rows")


class TestUsageCreditsAggregate:
    async def test_aggregate_credits_no_row_materialization(self):
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_NoRowResult(12))

        now = datetime(2025, 12, 31, 12, 0, 0, tzinfo=UTC)
        total = await get_current_period_usage_credits(db, user_id=123, now=now)

        assert total == 12
        db.execute.assert_awaited_once()
