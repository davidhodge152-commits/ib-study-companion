"""Credits and subscription routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import login_required

from helpers import current_user_id

bp = Blueprint("billing", __name__)


@bp.route("/api/credits/balance")
@login_required
def api_credits_balance():
    uid = current_user_id()
    from credit_store import CreditStoreDB
    store = CreditStoreDB(uid)
    return jsonify({
        "balance": store.balance(),
        "transactions": store.transaction_history(limit=20),
    })


@bp.route("/api/credits/purchase", methods=["POST"])
@login_required
def api_credits_purchase():
    data = request.get_json()
    amount = int(data.get("amount", 0))
    if amount <= 0:
        return jsonify({"error": "Invalid amount"}), 400
    uid = current_user_id()
    from credit_store import CreditStoreDB
    store = CreditStoreDB(uid)
    result = store.credit(amount, "purchase", f"Purchased {amount} credits")
    return jsonify(result)


@bp.route("/api/subscription/current")
@login_required
def api_subscription_current():
    uid = current_user_id()
    from subscription_store import SubscriptionStoreDB
    store = SubscriptionStoreDB(uid)
    plan = store.current_plan()
    limits = store.plan_limits()
    return jsonify({"plan": plan, "limits": limits})


@bp.route("/api/subscription/upgrade", methods=["POST"])
@login_required
def api_subscription_upgrade():
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
