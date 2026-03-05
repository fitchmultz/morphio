"""Purpose: Verify Stripe webhook boundary validation.
Responsibilities: Assert required security headers are enforced before webhook processing.
Scope: Route-level coverage for the public `/billing/webhook` ingress.
Usage: Executed by pytest in the backend integration suite.
Invariants/Assumptions: Missing `Stripe-Signature` must fail request validation before Stripe logic runs.
"""

import pytest
from pydantic import SecretStr

from app.config import settings


@pytest.mark.asyncio
async def test_billing_webhook_requires_stripe_signature_header(client, monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SecretStr("whsec_test"))

    response = await client.post("/billing/webhook", content=b"{}")

    assert response.status_code == 400
    payload = response.json()
    assert payload["message"] == "Field required"
    assert payload["data"]["error_type"] == "RequestValidationError"
    assert payload["data"]["details"]["errors"][0]["loc"] == ["header", "Stripe-Signature"]
