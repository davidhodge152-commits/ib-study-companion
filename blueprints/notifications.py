"""Notification and push subscription routes."""

from __future__ import annotations

import os
from dataclasses import asdict

from flask import Blueprint, jsonify, request
from flask_login import login_required

from helpers import current_user_id, generate_pending_notifications
from db_stores import NotificationStoreDB, PushSubscriptionStoreDB

bp = Blueprint("notifications", __name__)


@bp.route("/api/notifications")
@login_required
def api_notifications():
    """Return recent notifications and generate any pending ones."""
    from helpers import paginate_args, paginated_response

    uid = current_user_id()
    page, limit = paginate_args(default_limit=20, max_limit=50)
    generate_pending_notifications(uid)
    store = NotificationStoreDB(uid)
    all_notifs = store.recent(limit * page)
    total = len(all_notifs)
    start = (page - 1) * limit
    page_notifs = all_notifs[start:start + limit]
    result = paginated_response([asdict(n) for n in page_notifs], total, page, limit)
    result["notifications"] = result.pop("items")
    result["unread_count"] = store.unread_count()
    return jsonify(result)


@bp.route("/api/notifications/read", methods=["POST"])
@login_required
def api_notifications_read():
    data = request.get_json()
    notif_id = data.get("id", "")
    uid = current_user_id()
    store = NotificationStoreDB(uid)
    if notif_id == "all":
        store.mark_all_read()
    else:
        store.mark_read(notif_id)
    return jsonify({"success": True})


@bp.route("/api/notifications/dismiss", methods=["POST"])
@login_required
def api_notifications_dismiss():
    data = request.get_json()
    uid = current_user_id()
    store = NotificationStoreDB(uid)
    store.dismiss(data.get("id", ""))
    return jsonify({"success": True})


@bp.route("/api/push/subscribe", methods=["POST"])
@login_required
def api_push_subscribe():
    uid = current_user_id()
    data = request.get_json(force=True)
    sub = data.get("subscription", {})
    PushSubscriptionStoreDB.subscribe(
        user_id=uid,
        endpoint=sub.get("endpoint", ""),
        p256dh=sub.get("keys", {}).get("p256dh", ""),
        auth=sub.get("keys", {}).get("auth", ""),
    )
    return jsonify({"success": True})


@bp.route("/api/push/unsubscribe", methods=["POST"])
@login_required
def api_push_unsubscribe():
    data = request.get_json(force=True)
    PushSubscriptionStoreDB.unsubscribe(data.get("endpoint", ""))
    return jsonify({"success": True})


@bp.route("/api/push/vapid-key")
def api_vapid_key():
    key = os.environ.get("VAPID_PUBLIC_KEY", "")
    return jsonify({"publicKey": key})
