"""Stripe Payment Integration.

Handles checkout sessions, webhook processing, customer portal,
and credit purchases. Falls back gracefully when Stripe is unavailable.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Lazy import — Stripe is optional
_stripe = None


def _get_stripe():
    """Lazy-load the stripe module."""
    global _stripe
    if _stripe is None:
        try:
            import stripe
            _stripe = stripe
        except ImportError:
            raise RuntimeError(
                "stripe package not installed. Run: pip install stripe"
            )
    return _stripe


def is_stripe_available() -> bool:
    """Check if Stripe is configured and available."""
    try:
        _get_stripe()
        from flask import current_app
        key = current_app.config.get("STRIPE_SECRET_KEY", "")
        return bool(key)
    except Exception:
        return False


def _configure_stripe() -> None:
    """Set the Stripe API key from Flask config."""
    stripe = _get_stripe()
    from flask import current_app
    stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]


# ---------------------------------------------------------------------------
# Price mapping — maps internal plan IDs to Stripe Price IDs
# ---------------------------------------------------------------------------
PLAN_STRIPE_PRICES: dict[str, dict[str, str]] = {
    "explorer": {
        "monthly": "",  # Set via STRIPE_PRICE_EXPLORER_MONTHLY env var
        "annual": "",   # Set via STRIPE_PRICE_EXPLORER_ANNUAL env var
    },
    "scholar": {
        "monthly": "",
        "annual": "",
    },
    "diploma_pass": {
        "monthly": "",
        "annual": "",
    },
}

CREDIT_PACK_PRICES: dict[int, str] = {
    100: "",   # Set via STRIPE_PRICE_CREDITS_100 env var
    500: "",
    1000: "",
}


def init_stripe_prices(app) -> None:
    """Load Stripe Price IDs from app config / environment."""
    import os
    for plan in PLAN_STRIPE_PRICES:
        for interval in ("monthly", "annual"):
            env_key = f"STRIPE_PRICE_{plan.upper()}_{interval.upper()}"
            PLAN_STRIPE_PRICES[plan][interval] = os.environ.get(env_key, "")

    for amount in list(CREDIT_PACK_PRICES.keys()):
        env_key = f"STRIPE_PRICE_CREDITS_{amount}"
        CREDIT_PACK_PRICES[amount] = os.environ.get(env_key, "")


# ---------------------------------------------------------------------------
# Customer management
# ---------------------------------------------------------------------------

def get_or_create_customer(user_id: int, email: str, name: str = "") -> str:
    """Get existing Stripe customer ID or create a new one.

    Stores the stripe_customer_id in the users table.
    """
    _configure_stripe()
    stripe = _get_stripe()
    from database import get_db

    db = get_db()
    row = db.execute(
        "SELECT stripe_customer_id FROM users WHERE id = ?", (user_id,)
    ).fetchone()

    if row and row["stripe_customer_id"]:
        return row["stripe_customer_id"]

    customer = stripe.Customer.create(
        email=email,
        name=name or email,
        metadata={"user_id": str(user_id)},
    )

    db.execute(
        "UPDATE users SET stripe_customer_id = ? WHERE id = ?",
        (customer.id, user_id),
    )
    db.commit()
    return customer.id


# ---------------------------------------------------------------------------
# Checkout sessions
# ---------------------------------------------------------------------------

def create_checkout_session(
    user_id: int,
    email: str,
    plan_id: str,
    interval: str = "monthly",
    success_url: str = "",
    cancel_url: str = "",
) -> dict[str, Any]:
    """Create a Stripe Checkout Session for a subscription upgrade."""
    _configure_stripe()
    stripe = _get_stripe()
    from flask import current_app

    price_id = PLAN_STRIPE_PRICES.get(plan_id, {}).get(interval)
    if not price_id:
        raise ValueError(f"No Stripe price configured for {plan_id}/{interval}")

    base_url = current_app.config.get("BASE_URL", "http://localhost:5001")
    if not success_url:
        success_url = f"{base_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
    if not cancel_url:
        cancel_url = f"{base_url}/billing/cancel"

    customer_id = get_or_create_customer(user_id, email)

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": str(user_id),
            "plan_id": plan_id,
            "interval": interval,
        },
        subscription_data={
            "trial_period_days": 14,
            "metadata": {
                "user_id": str(user_id),
                "plan_id": plan_id,
            },
        },
    )

    return {
        "session_id": session.id,
        "url": session.url,
    }


def create_credit_checkout(
    user_id: int,
    email: str,
    credit_amount: int,
    success_url: str = "",
    cancel_url: str = "",
) -> dict[str, Any]:
    """Create a Stripe Checkout Session for a one-time credit purchase."""
    _configure_stripe()
    stripe = _get_stripe()
    from flask import current_app

    price_id = CREDIT_PACK_PRICES.get(credit_amount)
    if not price_id:
        raise ValueError(f"No Stripe price configured for {credit_amount} credits")

    base_url = current_app.config.get("BASE_URL", "http://localhost:5001")
    if not success_url:
        success_url = f"{base_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
    if not cancel_url:
        cancel_url = f"{base_url}/billing/cancel"

    customer_id = get_or_create_customer(user_id, email)

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="payment",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": str(user_id),
            "credit_amount": str(credit_amount),
            "type": "credit_purchase",
        },
    )

    return {
        "session_id": session.id,
        "url": session.url,
    }


# ---------------------------------------------------------------------------
# Customer portal
# ---------------------------------------------------------------------------

def create_portal_session(user_id: int, email: str) -> dict[str, str]:
    """Create a Stripe Customer Portal session for managing subscriptions."""
    _configure_stripe()
    stripe = _get_stripe()
    from flask import current_app

    customer_id = get_or_create_customer(user_id, email)
    base_url = current_app.config.get("BASE_URL", "http://localhost:5001")

    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{base_url}/dashboard",
    )

    return {"url": session.url}


# ---------------------------------------------------------------------------
# Webhook handling
# ---------------------------------------------------------------------------

def verify_webhook_signature(payload: bytes, sig_header: str, secret: str) -> dict:
    """Verify Stripe webhook signature and return the event object."""
    stripe = _get_stripe()
    event = stripe.Webhook.construct_event(payload, sig_header, secret)
    return event


def handle_webhook_event(event: dict) -> dict[str, Any]:
    """Process a verified Stripe webhook event.

    Returns a dict describing the action taken.
    """
    event_type = event.get("type", "")
    data_obj = event.get("data", {}).get("object", {})

    handlers = {
        "checkout.session.completed": _handle_checkout_completed,
        "customer.subscription.updated": _handle_subscription_updated,
        "customer.subscription.deleted": _handle_subscription_deleted,
        "invoice.payment_failed": _handle_payment_failed,
        "invoice.payment_succeeded": _handle_invoice_paid,
    }

    handler = handlers.get(event_type)
    if handler:
        return handler(data_obj)

    logger.info("Unhandled Stripe event type: %s", event_type)
    return {"action": "ignored", "event_type": event_type}


def _handle_checkout_completed(session: dict) -> dict[str, Any]:
    """Handle successful checkout — activate subscription or credit purchase."""
    metadata = session.get("metadata", {})
    user_id = metadata.get("user_id")
    if not user_id:
        logger.warning("checkout.session.completed missing user_id in metadata")
        return {"action": "skipped", "reason": "no user_id"}

    user_id = int(user_id)
    mode = session.get("mode", "")

    if mode == "subscription":
        plan_id = metadata.get("plan_id", "")
        if plan_id:
            from subscription_store import SubscriptionStoreDB
            store = SubscriptionStoreDB(user_id)
            store.upgrade(plan_id)

            # Store Stripe subscription ID
            stripe_sub_id = session.get("subscription", "")
            if stripe_sub_id:
                from database import get_db
                db = get_db()
                db.execute(
                    "UPDATE user_subscriptions SET stripe_subscription_id = ? "
                    "WHERE user_id = ?",
                    (stripe_sub_id, user_id),
                )
                db.commit()

            logger.info("Subscription activated: user=%s plan=%s", user_id, plan_id)
            return {"action": "subscription_activated", "user_id": user_id, "plan_id": plan_id}

    elif mode == "payment":
        credit_amount = metadata.get("credit_amount")
        if credit_amount:
            from credit_store import CreditStoreDB
            store = CreditStoreDB(user_id)
            store.credit(int(credit_amount), "purchase", f"Stripe purchase: {credit_amount} credits")
            logger.info("Credits purchased: user=%s amount=%s", user_id, credit_amount)
            return {"action": "credits_purchased", "user_id": user_id, "amount": int(credit_amount)}

    return {"action": "checkout_processed", "mode": mode}


def _handle_subscription_updated(subscription: dict) -> dict[str, Any]:
    """Handle subscription changes (upgrade, downgrade, renewal)."""
    metadata = subscription.get("metadata", {})
    user_id = metadata.get("user_id")
    if not user_id:
        return {"action": "skipped", "reason": "no user_id"}

    user_id = int(user_id)
    status = subscription.get("status", "")
    plan_id = metadata.get("plan_id", "")

    if status == "active" and plan_id:
        from subscription_store import SubscriptionStoreDB
        store = SubscriptionStoreDB(user_id)
        store.upgrade(plan_id)
        return {"action": "subscription_updated", "user_id": user_id, "plan_id": plan_id}

    return {"action": "subscription_update_noted", "status": status}


def _handle_subscription_deleted(subscription: dict) -> dict[str, Any]:
    """Handle subscription cancellation."""
    metadata = subscription.get("metadata", {})
    user_id = metadata.get("user_id")
    if not user_id:
        return {"action": "skipped", "reason": "no user_id"}

    user_id = int(user_id)
    from subscription_store import SubscriptionStoreDB
    store = SubscriptionStoreDB(user_id)
    store.cancel()

    # Downgrade to free
    store.upgrade("free")
    logger.info("Subscription cancelled: user=%s", user_id)
    return {"action": "subscription_cancelled", "user_id": user_id}


def _handle_payment_failed(invoice: dict) -> dict[str, Any]:
    """Handle failed payment — notify user."""
    customer_id = invoice.get("customer", "")
    if not customer_id:
        return {"action": "skipped", "reason": "no customer"}

    from database import get_db
    db = get_db()
    row = db.execute(
        "SELECT id FROM users WHERE stripe_customer_id = ?", (customer_id,)
    ).fetchone()

    if row:
        user_id = row["id"]
        # Create a notification about the failed payment
        try:
            from profile import Notification
            from db_stores import NotificationStoreDB
            from datetime import datetime
            store = NotificationStoreDB(user_id)
            store.add(Notification(
                id=f"payment_failed_{datetime.now().isoformat()}",
                type="payment_failed",
                title="Payment failed",
                body="Your subscription payment failed. Please update your payment method.",
                created_at=datetime.now().isoformat(),
                action_url="/billing",
            ))
        except Exception:
            logger.exception("Failed to create payment failure notification")

        logger.warning("Payment failed: user=%s", user_id)
        return {"action": "payment_failed_notified", "user_id": user_id}

    return {"action": "payment_failed", "customer": customer_id}


def _handle_invoice_paid(invoice: dict) -> dict[str, Any]:
    """Handle successful invoice payment (subscription renewal)."""
    customer_id = invoice.get("customer", "")
    if not customer_id:
        return {"action": "skipped", "reason": "no customer"}

    # On renewal, re-allocate monthly credits
    from database import get_db
    db = get_db()
    row = db.execute(
        "SELECT id FROM users WHERE stripe_customer_id = ?", (customer_id,)
    ).fetchone()

    if row:
        user_id = row["id"]
        from subscription_store import SubscriptionStoreDB, PLAN_CREDITS
        sub_store = SubscriptionStoreDB(user_id)
        plan = sub_store.current_plan()
        plan_id = plan.get("plan_id", "free")
        credits = PLAN_CREDITS.get(plan_id, 0)
        if credits > 0:
            from credit_store import CreditStoreDB
            CreditStoreDB(user_id).allocate_monthly(credits)
            logger.info("Monthly credits allocated on renewal: user=%s credits=%s", user_id, credits)
            return {"action": "credits_allocated", "user_id": user_id, "credits": credits}

    return {"action": "invoice_paid", "customer": customer_id}
