"""
Thin wrapper around Razorpay's test-mode API.

Day 7-8 TODO: replace the stubbed calls below with real `razorpay` SDK
calls once you have test API keys. Keep the function signatures the same
so nothing upstream (agent/policy/audit) needs to change.

Install when ready:  pip install razorpay
Docs: https://razorpay.com/docs/api/payments/payment-links/
"""
import os
import uuid

from app.models import ExecutedAction

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

# Toggle this once real keys are wired up.
USE_REAL_API = bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET)


def _mock_call(sku: str, discount_pct: float) -> ExecutedAction:
    """Simulated success path — good enough for Day 1-6 development
    before Razorpay keys are plugged in."""
    return ExecutedAction(
        sku=sku,
        action_type="payment_link_update",
        razorpay_ref=f"mock_ref_{uuid.uuid4().hex[:10]}",
        status="success",
        detail=f"[MOCK] Applied {discount_pct}% discount",
    )


def apply_discount(sku: str, discount_pct: float, amount_paise: int) -> ExecutedAction:
    """Executes a policy-approved discount as a Razorpay action.

    IMPORTANT: this function should only ever be called with a
    PolicyDecision.approved == True. Do not call this directly from
    the agent — always route through policy.evaluate() first.
    """
    if not USE_REAL_API:
        return _mock_call(sku, discount_pct)

    try:
        import razorpay  # local import so the mock path works without the package

        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        new_amount = int(amount_paise * (1 - discount_pct / 100))
        # Example: create a payment link reflecting the discounted amount.
        # Adjust to order-amount-update if that fits your flow better.
        link = client.payment_link.create({
            "amount": new_amount,
            "currency": "INR",
            "description": f"Discounted offer for {sku} ({discount_pct}% off)",
        })
        return ExecutedAction(
            sku=sku, action_type="payment_link_update",
            razorpay_ref=link.get("id"), status="success",
            detail=f"Applied {discount_pct}% discount",
        )
    except Exception as e:  # noqa: BLE001 — deliberately broad for the demo failure case
        return ExecutedAction(
            sku=sku, action_type="payment_link_update",
            razorpay_ref=None, status="failed",
            detail=f"Razorpay API error: {e}",
        )
