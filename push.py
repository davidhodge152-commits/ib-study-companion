"""
Web Push Notification sender.

Uses pywebpush with VAPID authentication to send push notifications
to subscribed users.
"""

from __future__ import annotations

import json
import os

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
