"""Stripe billing endpoints.

Provides checkout session creation and webhook handling for subscription management.
"""

import logging
from typing import Annotated

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..models.subscription import Subscription
from ..models.user import User
from ..services.security import get_current_user
from ..utils.decorators import require_auth
from ..utils.enums import ResponseStatus
from ..utils.response_utils import create_response, utc_now
from ..utils.route_helpers import common_responses, handle_route_errors

logger = logging.getLogger(__name__)


class CheckoutSessionData(BaseModel):
    """Data returned from checkout session creation."""

    checkout_url: str = Field(..., description="URL to redirect user to Stripe checkout")
    session_id: str = Field(..., description="Stripe session ID")


class PortalSessionData(BaseModel):
    """Data returned from portal session creation."""

    portal_url: str = Field(..., description="URL to redirect user to Stripe billing portal")


router = APIRouter(prefix="/billing", tags=["Billing"])


def get_stripe_client() -> stripe.StripeClient | None:
    """Get configured Stripe client, or None if not configured."""
    secret_key = settings.STRIPE_SECRET_KEY.get_secret_value()
    if not secret_key:
        return None
    return stripe.StripeClient(secret_key)


@router.post(
    "/checkout-session",
    operation_id="create_checkout_session",
    responses={
        200: {"description": "Checkout session created"},
        400: {"description": "Invalid plan"},
        503: {"description": "Stripe not configured"},
        **common_responses,
    },
)
@require_auth
@handle_route_errors
async def create_checkout_session(
    plan: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Create a Stripe Checkout Session for upgrading to a paid plan.

    Returns a URL to redirect the user to Stripe's hosted checkout page.
    """
    client = get_stripe_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not configured",
        )

    # Map plan to price ID
    price_id = None
    if plan.lower() == "pro":
        price_id = settings.STRIPE_PRO_PRICE_ID
    elif plan.lower() == "enterprise":
        price_id = settings.STRIPE_ENTERPRISE_PRICE_ID
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown plan: {plan}. Valid options: pro, enterprise",
        )

    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Price ID not configured for plan: {plan}",
        )

    # Get or create Stripe customer
    customer_id = current_user.stripe_customer_id
    if not customer_id:
        customer = client.customers.create(
            params={
                "email": current_user.email,
                "metadata": {"user_id": str(current_user.id)},
            }
        )
        customer_id = customer.id
        current_user.stripe_customer_id = customer_id
        await db.commit()

    # Create checkout session
    session = client.checkout.sessions.create(
        params={
            "customer": customer_id,
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": f"{settings.FRONTEND_URL}/profile?checkout=success",
            "cancel_url": f"{settings.FRONTEND_URL}/profile?checkout=canceled",
            "metadata": {"user_id": str(current_user.id), "plan": plan},
        }
    )

    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Checkout session created",
        data={"checkout_url": session.url, "session_id": session.id},
    )


@router.post(
    "/portal-session",
    operation_id="create_portal_session",
    responses={
        200: {"description": "Portal session created"},
        400: {"description": "No Stripe customer found"},
        503: {"description": "Stripe not configured"},
        **common_responses,
    },
)
@require_auth
@handle_route_errors
async def create_portal_session(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Create a Stripe Customer Portal session for managing subscriptions.

    Returns a URL to redirect the user to Stripe's billing portal.
    """
    client = get_stripe_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not configured",
        )

    if not current_user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing account found. Please subscribe to a plan first.",
        )

    session = client.billing_portal.sessions.create(
        params={
            "customer": current_user.stripe_customer_id,
            "return_url": f"{settings.FRONTEND_URL}/profile",
        }
    )

    return create_response(
        status=ResponseStatus.SUCCESS,
        message="Portal session created",
        data={"portal_url": session.url},
    )


@router.post(
    "/webhook",
    operation_id="stripe_webhook",
    include_in_schema=False,  # Webhook endpoints shouldn't be in public API docs
)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Stripe webhook events for subscription lifecycle management.
    """
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET.get_secret_value()
    if not webhook_secret:
        logger.warning("Stripe webhook secret not configured, ignoring webhook")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook not configured",
        )

    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, webhook_secret)
    except ValueError as e:
        logger.error(f"Invalid webhook payload: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload")
    except stripe.SignatureVerificationError as e:
        logger.error(f"Invalid webhook signature: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    event_type = event["type"]
    event_data = event["data"]["object"]

    logger.info(f"Received Stripe webhook: {event_type}")

    # Handle different event types
    if event_type == "checkout.session.completed":
        await handle_checkout_completed(event_data, db)
    elif event_type == "customer.subscription.updated":
        await handle_subscription_updated(event_data, db)
    elif event_type == "customer.subscription.deleted":
        await handle_subscription_deleted(event_data, db)
    elif event_type == "invoice.payment_failed":
        await handle_payment_failed(event_data, db)
    else:
        logger.debug(f"Unhandled webhook event type: {event_type}")

    return {"received": True}


async def handle_checkout_completed(session: dict, db: AsyncSession):
    """Handle successful checkout session."""
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")
    metadata = session.get("metadata", {})
    user_id = metadata.get("user_id")
    plan = metadata.get("plan", "pro")

    if not user_id or not customer_id:
        logger.warning(f"Checkout session missing user_id or customer: {session.get('id')}")
        return

    # Find user by ID
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        logger.warning(f"User not found for checkout session: {user_id}")
        return

    # Update user's Stripe info
    user.stripe_customer_id = customer_id
    user.subscription_status = "active"

    # Create or update subscription record
    sub_result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user.id, Subscription.deleted_at.is_(None)
        )
    )
    existing_sub = sub_result.scalar_one_or_none()

    if existing_sub:
        existing_sub.stripe_subscription_id = subscription_id
        existing_sub.plan = plan
        existing_sub.status = "active"
        existing_sub.updated_at = utc_now()
    else:
        new_sub = Subscription(
            user_id=user.id,
            stripe_subscription_id=subscription_id,
            plan=plan,
            status="active",
            created_at=utc_now(),
        )
        db.add(new_sub)

    await db.commit()
    logger.info(f"Checkout completed for user {user_id}, plan: {plan}")


async def handle_subscription_updated(subscription: dict, db: AsyncSession):
    """Handle subscription status changes."""
    customer_id = subscription.get("customer")
    status_val = subscription.get("status")

    if not customer_id:
        return

    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    user = result.scalar_one_or_none()
    if not user:
        logger.warning(f"User not found for customer: {customer_id}")
        return

    user.subscription_status = status_val

    # Update subscription record
    sub_result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user.id, Subscription.deleted_at.is_(None)
        )
    )
    existing_sub = sub_result.scalar_one_or_none()
    if existing_sub:
        existing_sub.status = status_val
        existing_sub.updated_at = utc_now()

    await db.commit()
    logger.info(f"Subscription updated for user {user.id}: {status_val}")


async def handle_subscription_deleted(subscription: dict, db: AsyncSession):
    """Handle subscription cancellation/deletion."""
    customer_id = subscription.get("customer")

    if not customer_id:
        return

    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    user = result.scalar_one_or_none()
    if not user:
        return

    user.subscription_status = "canceled"

    # Soft-delete subscription record
    sub_result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user.id, Subscription.deleted_at.is_(None)
        )
    )
    existing_sub = sub_result.scalar_one_or_none()
    if existing_sub:
        existing_sub.status = "canceled"
        existing_sub.soft_delete()

    await db.commit()
    logger.info(f"Subscription canceled for user {user.id}")


async def handle_payment_failed(invoice: dict, db: AsyncSession):
    """Handle failed payment."""
    customer_id = invoice.get("customer")

    if not customer_id:
        return

    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    user = result.scalar_one_or_none()
    if not user:
        return

    user.subscription_status = "past_due"

    # Update subscription record
    sub_result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user.id, Subscription.deleted_at.is_(None)
        )
    )
    existing_sub = sub_result.scalar_one_or_none()
    if existing_sub:
        existing_sub.status = "past_due"
        existing_sub.updated_at = utc_now()

    await db.commit()
    logger.info(f"Payment failed for user {user.id}")
