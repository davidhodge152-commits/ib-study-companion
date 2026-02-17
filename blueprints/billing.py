"""Credits, subscription, and Stripe payment routes."""

from __future__ import annotations

import logging
from typing import Any

from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user

from helpers import current_user_id

logger = logging.getLogger(__name__)

bp = Blueprint("billing", __name__)


@bp.record_once
def _exempt_webhook_from_csrf(state: Any) -> None:
    """Exempt the Stripe webhook endpoint from CSRF protection."""
    csrf = state.app.extensions.get("csrf")
    if csrf:
        csrf.exempt(api_billing_webhook)


# ---------------------------------------------------------------------------
# Credit endpoints
# ---------------------------------------------------------------------------

@bp.route("/api/credits/balance")
@login_required
def api_credits_balance() -> tuple[Any, int] | Any:
    uid = current_user_id()
    from credit_store import CreditStoreDB
    store = CreditStoreDB(uid)
    return jsonify({
        "balance": store.balance(),
        "transactions": store.transaction_history(limit=20),
    })


@bp.route("/api/credits/purchase", methods=["POST"])
@login_required
def api_credits_purchase() -> tuple[Any, int] | Any:
    data = request.get_json()
    amount = int(data.get("amount", 0))
    if amount <= 0:
        return jsonify({"error": "Invalid amount"}), 400
    uid = current_user_id()
    from credit_store import CreditStoreDB
    store = CreditStoreDB(uid)
    result = store.credit(amount, "purchase", f"Purchased {amount} credits")
    return jsonify(result)


@bp.route("/api/credits/buy", methods=["POST"])
@login_required
def api_credits_buy_stripe() -> tuple[Any, int] | Any:
    """Buy credits via Stripe Checkout."""
    from stripe_integration import is_stripe_available, create_credit_checkout

    if not is_stripe_available():
        return jsonify({"error": "Payments not configured"}), 503

    data = request.get_json() or {}
    credit_amount = int(data.get("amount", 0))
    if credit_amount <= 0:
        return jsonify({"error": "Invalid credit amount"}), 400

    try:
        result = create_credit_checkout(
            user_id=current_user.id,
            email=current_user.email,
            credit_amount=credit_amount,
        )
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Stripe credit checkout error")
        return jsonify({"error": "Payment service error"}), 500


# ---------------------------------------------------------------------------
# Subscription endpoints
# ---------------------------------------------------------------------------

@bp.route("/api/subscription/current")
@login_required
def api_subscription_current() -> Any:
    uid = current_user_id()
    from subscription_store import SubscriptionStoreDB
    store = SubscriptionStoreDB(uid)
    plan = store.current_plan()
    limits = store.plan_limits()
    return jsonify({"plan": plan, "limits": limits})


@bp.route("/api/subscription/upgrade", methods=["POST"])
@login_required
def api_subscription_upgrade() -> tuple[Any, int] | Any:
    data = request.get_json()
    plan_id = data.get("plan_id", "")
    if not plan_id:
        return jsonify({"error": "Plan ID required"}), 400
    uid = current_user_id()
    from subscription_store import SubscriptionStoreDB
    store = SubscriptionStoreDB(uid)
    try:
        store.upgrade(plan_id)
        return jsonify({"success": True, "plan": store.current_plan()})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# ---------------------------------------------------------------------------
# Stripe Checkout
# ---------------------------------------------------------------------------

@bp.route("/api/billing/checkout", methods=["POST"])
@login_required
def api_billing_checkout() -> tuple[Any, int] | Any:
    """Create a Stripe Checkout Session for subscription upgrade."""
    from stripe_integration import is_stripe_available, create_checkout_session

    if not is_stripe_available():
        return jsonify({"error": "Payments not configured"}), 503

    data = request.get_json() or {}
    plan_id = data.get("plan_id", "")
    interval = data.get("interval", "monthly")

    if not plan_id:
        return jsonify({"error": "plan_id required"}), 400
    if interval not in ("monthly", "annual"):
        return jsonify({"error": "interval must be 'monthly' or 'annual'"}), 400

    try:
        result = create_checkout_session(
            user_id=current_user.id,
            email=current_user.email,
            plan_id=plan_id,
            interval=interval,
        )
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Stripe checkout error")
        return jsonify({"error": "Payment service error"}), 500


# ---------------------------------------------------------------------------
# Stripe Customer Portal
# ---------------------------------------------------------------------------

@bp.route("/api/billing/portal", methods=["POST"])
@login_required
def api_billing_portal() -> tuple[Any, int] | Any:
    """Create a Stripe Customer Portal session."""
    from stripe_integration import is_stripe_available, create_portal_session

    if not is_stripe_available():
        return jsonify({"error": "Payments not configured"}), 503

    try:
        result = create_portal_session(
            user_id=current_user.id,
            email=current_user.email,
        )
        return jsonify(result)
    except Exception as e:
        logger.exception("Stripe portal error")
        return jsonify({"error": "Payment service error"}), 500


# ---------------------------------------------------------------------------
# Stripe Webhook
# ---------------------------------------------------------------------------

@bp.route("/api/billing/webhook", methods=["POST"])
def api_billing_webhook() -> tuple[Any, int] | Any:
    """Handle Stripe webhook events.

    This endpoint is NOT behind login_required because Stripe calls it directly.
    Authentication is via webhook signature verification.
    CSRF is exempt — Stripe uses signature-based auth instead.
    """
    from stripe_integration import is_stripe_available

    if not is_stripe_available():
        return jsonify({"error": "Payments not configured"}), 503

    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")
    webhook_secret = current_app.config.get("STRIPE_WEBHOOK_SECRET", "")

    if not webhook_secret:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        return jsonify({"error": "Webhook not configured"}), 500

    try:
        from stripe_integration import verify_webhook_signature, handle_webhook_event
        event = verify_webhook_signature(payload, sig_header, webhook_secret)
        result = handle_webhook_event(event)
        logger.info("Webhook processed: %s -> %s", event.get("type"), result.get("action"))
        return jsonify({"status": "ok", **result})
    except ValueError:
        logger.warning("Invalid webhook payload")
        return jsonify({"error": "Invalid payload"}), 400
    except Exception as e:
        if "SignatureVerificationError" in type(e).__name__:
            logger.warning("Invalid webhook signature")
            return jsonify({"error": "Invalid signature"}), 400
        logger.exception("Webhook processing error")
        return jsonify({"error": "Webhook processing failed"}), 500


# ---------------------------------------------------------------------------
# Billing history
# ---------------------------------------------------------------------------

@bp.route("/api/billing/history")
@login_required
def api_billing_history() -> Any:
    """Return billing history (credit transactions + subscription info)."""
    uid = current_user_id()
    from credit_store import CreditStoreDB
    from subscription_store import SubscriptionStoreDB

    credit_store = CreditStoreDB(uid)
    sub_store = SubscriptionStoreDB(uid)

    return jsonify({
        "subscription": sub_store.current_plan(),
        "limits": sub_store.plan_limits(),
        "balance": credit_store.balance(),
        "transactions": credit_store.transaction_history(limit=50),
    })
