"""Purpose: Enforce usage quotas and persist monthly credit consumption.
Responsibilities: Calculate current-period usage, gate expensive operations, and increment counters.
Scope: Shared service functions used by generation and user-credit flows.
Usage: Called before and after quota-metered operations.
Invariants/Assumptions: Public demo quotas are fixed by plan and should fail with clear monthly-limit messaging rather than monetization prompts.
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...models.llm_usage import LLMUsageRecord
from ...models.quota_tier import QuotaTierAssignment
from ...models.usage import Usage
from ...models.user import User
from ...utils.enums import UsageType, UserRole
from ...utils.error_handlers import ApplicationException
from ...utils.response_utils import utc_now

logger = logging.getLogger(__name__)


def _current_monthly_usage_period(now: datetime) -> tuple[datetime, datetime]:
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        period_end = datetime(now.year + 1, 1, 1, tzinfo=UTC)
    else:
        period_end = datetime(now.year, now.month + 1, 1, tzinfo=UTC)
    return period_start, period_end


async def get_current_period_usage_credits(
    db: AsyncSession,
    user_id: int,
    *,
    now: datetime | None = None,
) -> int:
    if now is None:
        now = utc_now()

    period_start, period_end = _current_monthly_usage_period(now)
    usage_ts = func.coalesce(Usage.updated_at, Usage.created_at)
    result = await db.execute(
        select(func.coalesce(func.sum(Usage.usage_credits), 0)).where(
            Usage.user_id == user_id,
            Usage.deleted_at.is_(None),
            usage_ts >= period_start,
            usage_ts < period_end,
        )
    )
    return int(result.scalar_one() or 0)


async def check_usage_limit(
    db: AsyncSession, user_id: int, usage_type: UsageType = UsageType.OTHER
) -> bool:
    """
    Check if user has available credits without incrementing.

    Use this BEFORE expensive operations (like LLM generation) to fail fast.

    Args:
        db: Database session
        user_id: ID of the user to check
        usage_type: Type of usage being checked

    Returns:
        True if user has available credits

    Raises:
        ApplicationException: If user not found or usage limit exceeded (403)
    """
    user = await db.get(User, user_id)
    if not user:
        msg = f"User {user_id} not found in DB"
        logger.error(msg)
        raise ApplicationException(msg, status_code=404)

    # Admins always have access
    if user.role == UserRole.ADMIN:
        return True

    # Get current usage
    query = select(Usage).where(
        Usage.user_id == user_id,
        Usage.usage_type == usage_type.value,
        Usage.deleted_at.is_(None),
    )
    result = await db.execute(query)
    usage = result.scalar_one_or_none()

    current_credits = 0
    if usage:
        now = utc_now()
        # Check if usage should reset
        if usage.updated_at and (
            usage.updated_at.month != now.month or usage.updated_at.year != now.year
        ):
            current_credits = 0
        else:
            current_credits = usage.usage_credits

    # Get quota tier limit
    quota_tier = "free"
    quota_tier_result = await db.execute(
        select(QuotaTierAssignment).where(
            QuotaTierAssignment.user_id == user_id,
            QuotaTierAssignment.deleted_at.is_(None),
        )
    )
    quota_assignments = quota_tier_result.scalars().all()
    active_tier = next((record for record in quota_assignments if record.status == "active"), None)
    if active_tier:
        quota_tier = active_tier.tier.lower()

    tier_limit = settings.QUOTA_TIER_LIMITS.get(quota_tier, 50)
    cost = settings.USAGE_WEIGHTS.get(usage_type.value.upper(), 1)

    # Check if would exceed limit
    if current_credits + cost > tier_limit:
        msg = (
            f"You have reached the monthly usage limit for the '{quota_tier}' tier. "
            "Please wait for the monthly reset."
        )
        logger.warning(f"Usage limit check failed for user {user_id}: {msg}")
        raise ApplicationException(msg, status_code=403)

    return True


async def increment_usage(db: AsyncSession, user_id: int, usage_type: UsageType = UsageType.OTHER):
    """
    Increment usage for user_id, factoring in usage weighting from config.
    If user is ADMIN => skip plan usage check.
    Tier limits come from config as well.

    :param db: Database session
    :param user_id: ID of the user to increment usage for
    :param usage_type: Type of usage being tracked
    :raises ApplicationException: If user not found or usage limit exceeded
    """
    # 1) Retrieve the user to check role
    user = await db.get(User, user_id)
    if not user:
        msg = f"User {user_id} not found in DB"
        logger.error(msg)
        raise ApplicationException(msg, status_code=404)

    # 2) Look up or create a usage row for this user + usage_type
    query = select(Usage).where(
        Usage.user_id == user_id,
        Usage.usage_type == usage_type.value,
        Usage.deleted_at.is_(None),
    )
    result = await db.execute(query)
    usage = result.scalar_one_or_none()

    if not usage:
        usage = Usage(
            user_id=user_id,
            usage_type=usage_type.value,
            usage_count=0,
            usage_credits=0,
            created_at=utc_now(),
        )
        db.add(usage)

    now = utc_now()
    # If usage was last updated in a previous month, reset usage
    if usage.updated_at:
        if (usage.updated_at.month != now.month) or (usage.updated_at.year != now.year):
            usage.usage_count = 0
            usage.usage_credits = 0
            logger.debug(f"Monthly usage reset for user {user_id} / {usage_type.value}")
    else:
        usage.updated_at = now

    # 3) If user is ADMIN, skip quota-tier usage limit checks
    if user.role == UserRole.ADMIN:
        usage.usage_count += 1
        # Grab cost from config
        cost = settings.USAGE_WEIGHTS.get(usage_type.value.upper(), 1)
        usage.usage_credits += cost
        usage.last_used_at = now
        usage.updated_at = now
        await db.commit()
        await db.refresh(usage)
        logger.debug(
            f"(ADMIN) Usage updated for user {user_id}, "
            f"type={usage_type.value}, calls={usage.usage_count}, credits={usage.usage_credits}"
        )
        return

    # 4) Determine effective quota tier
    quota_tier = "free"
    quota_tier_result = await db.execute(
        select(QuotaTierAssignment).where(
            QuotaTierAssignment.user_id == user_id,
            QuotaTierAssignment.deleted_at.is_(None),
        )
    )
    quota_assignments = quota_tier_result.scalars().all()
    active_tier = next((record for record in quota_assignments if record.status == "active"), None)
    if active_tier:
        quota_tier = active_tier.tier.lower()

    tier_limit = settings.QUOTA_TIER_LIMITS.get(quota_tier, 50)
    cost = settings.USAGE_WEIGHTS.get(usage_type.value.upper(), 1)

    # 5) Check quota-tier limit
    if usage.usage_credits + cost > tier_limit:
        msg = (
            f"You have reached the monthly usage limit for the '{quota_tier}' tier. "
            "Please wait for the monthly reset."
        )
        logger.warning(f"Usage limit exceeded for user {user_id}: {msg}")
        raise ApplicationException(msg, status_code=403)

    # 6) Increment usage
    usage.usage_count += 1
    usage.usage_credits += cost
    usage.last_used_at = now
    usage.updated_at = now

    await db.commit()
    await db.refresh(usage)
    logger.debug(
        f"Usage updated for user {user_id}, type={usage_type.value}, "
        f"calls={usage.usage_count}, credits={usage.usage_credits}, tier={quota_tier}"
    )


async def record_llm_usage(
    db: AsyncSession,
    *,
    user_id: int,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    model_alias: str | None = None,
    content_id: int | None = None,
    operation: str | None = None,
    cost_usd: Decimal | None = None,
) -> LLMUsageRecord:
    """
    Record detailed LLM token usage for a single API call.

    This supplements increment_usage() by tracking the actual token counts,
    enabling cost estimation and detailed analytics.

    Args:
        db: Database session
        user_id: User who made the request
        provider: LLM provider (openai, anthropic, gemini)
        model: Actual model used (e.g., gpt-4o, claude-sonnet-4-20250514)
        input_tokens: Input/prompt tokens used
        output_tokens: Output/completion tokens used
        model_alias: User-facing model name if different (e.g., gpt-5.2-high)
        content_id: Optional linked content ID
        operation: Type of operation (content_generation, title_generation, chat)
        cost_usd: Optional estimated cost in USD

    Returns:
        The created LLMUsageRecord
    """
    record = LLMUsageRecord(
        user_id=user_id,
        provider=provider,
        model=model,
        model_alias=model_alias,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        content_id=content_id,
        operation=operation,
        cost_usd=cost_usd,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    logger.debug(
        f"LLM usage recorded: user={user_id}, provider={provider}, "
        f"model={model}, in={input_tokens}, out={output_tokens}"
    )
    return record
