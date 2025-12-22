import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...models.subscription import Subscription
from ...models.usage import Usage
from ...models.user import User
from ...utils.enums import UsageType, UserRole
from ...utils.error_handlers import ApplicationException
from ...utils.response_utils import utc_now

logger = logging.getLogger(__name__)


async def increment_usage(db: AsyncSession, user_id: int, usage_type: UsageType = UsageType.OTHER):
    """
    Increment usage for user_id, factoring in usage weighting from config.
    If user is ADMIN => skip plan usage check.
    Plan-limits come from config as well.

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

    # 3) If user is ADMIN, skip plan usage limit checks
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

    # 4) Determine subscription plan
    subscription_plan = "free"
    subscription_result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.deleted_at.is_(None),
        )
    )
    user_subscriptions = subscription_result.scalars().all()
    active_sub = next((sub for sub in user_subscriptions if sub.status == "active"), None)
    if active_sub:
        subscription_plan = active_sub.plan.lower()

    plan_limit = settings.SUBSCRIPTION_PLAN_LIMITS.get(subscription_plan, 50)
    cost = settings.USAGE_WEIGHTS.get(usage_type.value.upper(), 1)

    # 5) Check plan limit
    if usage.usage_credits + cost > plan_limit:
        msg = (
            f"You have reached the usage credit limit for your '{subscription_plan}' plan. "
            "Please upgrade your subscription or wait for the monthly reset."
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
        f"calls={usage.usage_count}, credits={usage.usage_credits}, plan={subscription_plan}"
    )
