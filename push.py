"""
Web Push Notification sender and scheduler.

Uses pywebpush with VAPID authentication to send push notifications
to subscribed users. Includes a background scheduler that analyzes
study patterns and sends timely reminders.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

from database import get_db


def send_push(user_id: int, title: str, body: str, url: str = "") -> int:
    """Send push notification to all subscriptions for a user.

    Returns the number of successful deliveries.
    """
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        return 0

    private_key = os.environ.get("VAPID_PRIVATE_KEY", "")
    claims_email = os.environ.get("VAPID_CLAIMS_EMAIL", "mailto:admin@example.com")

    if not private_key:
        return 0

    db = get_db()
    rows = db.execute(
        "SELECT endpoint, p256dh, auth FROM push_subscriptions WHERE user_id = ?",
        (user_id,),
    ).fetchall()

    sent = 0
    for row in rows:
        subscription_info = {
            "endpoint": row["endpoint"],
            "keys": {
                "p256dh": row["p256dh"],
                "auth": row["auth"],
            },
        }
        payload = json.dumps({
            "title": title,
            "body": body,
            "url": url,
        })
        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=private_key,
                vapid_claims={"sub": claims_email},
            )
            sent += 1
        except WebPushException as e:
            # If subscription is expired, remove it
            if e.response and e.response.status_code in (404, 410):
                db.execute(
                    "DELETE FROM push_subscriptions WHERE endpoint = ?",
                    (row["endpoint"],),
                )
                db.commit()
        except Exception:
            pass

    return sent


# ── Study Pattern Notifications ──────────────────────────────────────


def _find_inactive_subjects(user_id: int, days_threshold: int = 5) -> list[dict]:
    """Find subjects a user hasn't practiced in N days, along with their weakest command term."""
    db = get_db()
    rows = db.execute(
        "SELECT subject_display, MAX(timestamp) as last_active, "
        "MIN(percentage) as weakest_pct "
        "FROM grades WHERE user_id = ? "
        "GROUP BY subject_display",
        (user_id,),
    ).fetchall()

    cutoff = (datetime.now() - timedelta(days=days_threshold)).isoformat()
    inactive = []
    for r in rows:
        if r["last_active"] < cutoff:
            # Find their weakest command term in this subject
            weak = db.execute(
                "SELECT command_term, AVG(percentage) as avg_pct "
                "FROM grades WHERE user_id = ? AND subject_display = ? "
                "GROUP BY command_term ORDER BY avg_pct ASC LIMIT 1",
                (user_id, r["subject_display"]),
            ).fetchone()
            inactive.append({
                "subject": r["subject_display"],
                "days_since": (datetime.now() - datetime.fromisoformat(r["last_active"])).days,
                "weakest_command_term": weak["command_term"] if weak else None,
            })
    return inactive


def _check_streak_at_risk(user_id: int) -> bool:
    """Check if user hasn't studied today and has an active streak."""
    db = get_db()
    gam = db.execute(
        "SELECT current_streak FROM gamification WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if not gam or gam["current_streak"] < 2:
        return False

    today = datetime.now().strftime("%Y-%m-%d")
    activity = db.execute(
        "SELECT 1 FROM grades WHERE user_id = ? AND timestamp LIKE ?",
        (user_id, f"{today}%"),
    ).fetchone()
    return activity is None  # No activity today = streak at risk


def send_study_reminders(app) -> int:
    """Check all subscribed users and send appropriate study reminders.

    Call this from a background scheduler (e.g. APScheduler, cron).
    Returns total notifications sent.
    """
    total_sent = 0
    with app.app_context():
        db = get_db()
        # Get all users who have push subscriptions
        users = db.execute(
            "SELECT DISTINCT user_id FROM push_subscriptions"
        ).fetchall()

        for user_row in users:
            uid = user_row["user_id"]

            # 1. Streak-at-risk notification
            if _check_streak_at_risk(uid):
                total_sent += send_push(
                    uid,
                    "Your streak is at risk!",
                    "You haven't studied today. A quick 10-minute session keeps your streak alive.",
                    "/study",
                )
                continue  # One notification per cycle per user

            # 2. Inactive subject reminders
            inactive = _find_inactive_subjects(uid, days_threshold=5)
            if inactive:
                subj = inactive[0]
                body = f"You haven't touched {subj['subject']} in {subj['days_since']} days."
                if subj["weakest_command_term"]:
                    body += f" Your weakest command term there is '{subj['weakest_command_term']}'. 10 minutes?"
                total_sent += send_push(uid, "Time to review?", body, "/study")

    return total_sent


def init_scheduler(app):
    """Legacy entry point — scheduling moved to scheduler.py.

    Kept for backwards compatibility. Use scheduler.init_scheduler instead.
    """
    from scheduler import init_scheduler as _init
    return _init(app)
