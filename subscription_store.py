"""Subscription Tiers & Feature Gating.

Manages user subscription plans, feature access, and plan limits.
Provides @requires_plan decorator for endpoint gating.
"""

from __future__ import annotations

import json
from datetime import datetime
from functools import wraps

from flask import jsonify
from flask_login import current_user

from database import get_db


PLAN_FEATURES = {
    "free": ["text_tutoring", "grading", "flashcards", "study_plan"],
    "explorer": [
        "text_tutoring", "grading", "flashcards", "study_plan",
        "oral_practice", "question_gen", "data_analysis", "vision_agent",
    ],
    "scholar": [
        "text_tutoring", "grading", "flashcards", "study_plan",
        "oral_practice", "question_gen", "data_analysis", "vision_agent",
        "examiner_review", "admissions", "batch_grade",
    ],
    "diploma_pass": ["all"],
}

PLAN_CREDITS = {
    "free": 0,
    "explorer": 200,
    "scholar": 500,
    "diploma_pass": 1000,
}

PLAN_ORDER = ["free", "explorer", "scholar", "diploma_pass"]

PLAN_DISPLAY = {
    "free": "Free",
    "explorer": "Explorer",
    "scholar": "Scholar",
    "diploma_pass": "Diploma Pass",
}


class SubscriptionStoreDB:
    """DB-backed subscription management."""

    def __init__(self, user_id: int):
        self.user_id = user_id

    def _ensure(self) -> None:
        """Create subscription row if missing (defaults to free)."""
        db = get_db()
        existing = db.execute(
            "SELECT user_id FROM user_subscriptions WHERE user_id = ?",
            (self.user_id,),
        ).fetchone()
        if not existing:
            db.execute(
                "INSERT INTO user_subscriptions (user_id, plan_id, status, started_at) "
                "VALUES (?, 'free', 'active', ?)",
                (self.user_id, datetime.now().isoformat()),
            )
            db.commit()

    def current_plan(self) -> dict:
        """Return current plan details."""
        self._ensure()
        db = get_db()
        row = db.execute(
            "SELECT us.plan_id, us.status, us.started_at, us.expires_at, "
            "sp.name, sp.monthly_credits, sp.price_monthly, sp.price_annual, "
            "sp.max_subjects "
            "FROM user_subscriptions us "
            "JOIN subscription_plans sp ON us.plan_id = sp.id "
            "WHERE us.user_id = ?",
            (self.user_id,),
        ).fetchone()
        if not row:
            return {"plan_id": "free", "name": "Free", "status": "active",
                    "monthly_credits": 0, "max_subjects": 3}
        return dict(row)

    def upgrade(self, plan_id: str) -> None:
        """Upgrade user to a new plan."""
        if plan_id not in PLAN_ORDER:
            raise ValueError(f"Invalid plan: {plan_id}")
        self._ensure()
        db = get_db()
        now = datetime.now().isoformat()
        db.execute(
            "UPDATE user_subscriptions SET plan_id = ?, status = 'active', "
            "started_at = ?, cancelled_at = '' WHERE user_id = ?",
            (plan_id, now, self.user_id),
        )
        db.commit()

        # Allocate monthly credits
        credits = PLAN_CREDITS.get(plan_id, 0)
        if credits > 0:
            from credit_store import CreditStoreDB
            CreditStoreDB(self.user_id).allocate_monthly(credits)

    def cancel(self) -> None:
        """Cancel current subscription (reverts to free at period end)."""
        self._ensure()
        db = get_db()
        now = datetime.now().isoformat()
        db.execute(
            "UPDATE user_subscriptions SET status = 'cancelled', cancelled_at = ? "
            "WHERE user_id = ?",
            (now, self.user_id),
        )
        db.commit()

    def is_feature_allowed(self, feature: str) -> bool:
        """Check if the user's plan includes a feature."""
        plan = self.current_plan()
        plan_id = plan.get("plan_id", "free")
        features = PLAN_FEATURES.get(plan_id, [])
        return "all" in features or feature in features

    def plan_limits(self) -> dict:
        """Return plan limits for the current user."""
        plan = self.current_plan()
        plan_id = plan.get("plan_id", "free")
        return {
            "plan_id": plan_id,
            "name": plan.get("name", PLAN_DISPLAY.get(plan_id, "Free")),
            "max_subjects": plan.get("max_subjects", 3),
            "monthly_credits": PLAN_CREDITS.get(plan_id, 0),
            "features": PLAN_FEATURES.get(plan_id, []),
        }


def requires_plan(min_plan: str):
    """Decorator that gates an endpoint behind a minimum subscription tier."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            uid = current_user.id if current_user.is_authenticated else None
            if uid is None:
                return jsonify({"error": "Authentication required"}), 401

            store = SubscriptionStoreDB(uid)
            plan = store.current_plan()
            user_plan = plan.get("plan_id", "free")

            min_idx = PLAN_ORDER.index(min_plan) if min_plan in PLAN_ORDER else 0
            user_idx = PLAN_ORDER.index(user_plan) if user_plan in PLAN_ORDER else 0

            if user_idx < min_idx:
                return jsonify({
                    "error": f"Upgrade to {PLAN_DISPLAY.get(min_plan, min_plan)} to access this feature",
                    "required_plan": min_plan,
                    "current_plan": user_plan,
                }), 403

            return f(*args, **kwargs)
        return decorated
    return decorator
