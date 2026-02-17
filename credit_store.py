"""Credit/Token Economy — Manages credit balances, transactions, and feature gating.

Provides CreditStoreDB for ledger operations and a @requires_credits decorator
for auto-gating API endpoints behind credit checks.
"""

from __future__ import annotations

import json
from datetime import datetime
from functools import wraps

from flask import jsonify, request
from flask_login import current_user

from database import get_db


FEATURE_COSTS = {
    "oral_practice": 50,
    "examiner_review": 500,
    "batch_grade_per_student": 20,
    "parametric_questions": 10,
    "data_analysis": 25,
    "admissions_profile": 100,
    "personal_statement": 200,
}


class CreditStoreDB:
    """DB-backed credit ledger."""

    def __init__(self, user_id: int):
        self.user_id = user_id

    def _ensure(self) -> None:
        """Create balance row if missing."""
        db = get_db()
        db.execute(
            "INSERT OR IGNORE INTO credit_balances (user_id) VALUES (?)",
            (self.user_id,),
        )
        db.commit()

    def balance(self) -> int:
        """Current credit balance."""
        self._ensure()
        db = get_db()
        row = db.execute(
            "SELECT balance FROM credit_balances WHERE user_id = ?",
            (self.user_id,),
        ).fetchone()
        return row["balance"] if row else 0

    def has_credits(self, amount: int) -> bool:
        """Check if user has at least `amount` credits."""
        return self.balance() >= amount

    def debit(self, amount: int, feature: str, description: str = "") -> dict:
        """Deduct credits. Returns {success, balance_after, tx_id}."""
        self._ensure()
        db = get_db()
        current = self.balance()
        if current < amount:
            return {"success": False, "balance_after": current, "tx_id": None}

        new_balance = current - amount
        now = datetime.now().isoformat()

        db.execute(
            "UPDATE credit_balances SET balance = ? WHERE user_id = ?",
            (new_balance, self.user_id),
        )
        cur = db.execute(
            "INSERT INTO credit_transactions "
            "(user_id, amount, type, feature, description, balance_after, created_at) "
            "VALUES (?, ?, 'usage', ?, ?, ?, ?)",
            (self.user_id, -amount, feature, description, new_balance, now),
        )
        db.commit()
        return {"success": True, "balance_after": new_balance, "tx_id": cur.lastrowid}

    def credit(self, amount: int, tx_type: str = "purchase", description: str = "") -> dict:
        """Add credits. Returns {success, balance_after, tx_id}."""
        self._ensure()
        db = get_db()
        current = self.balance()
        new_balance = current + amount
        now = datetime.now().isoformat()

        update_clause = "UPDATE credit_balances SET balance = ?"
        params: list = [new_balance]
        if tx_type == "purchase":
            update_clause += ", lifetime_purchased = lifetime_purchased + ?"
            params.append(amount)
        update_clause += " WHERE user_id = ?"
        params.append(self.user_id)

        db.execute(update_clause, params)
        cur = db.execute(
            "INSERT INTO credit_transactions "
            "(user_id, amount, type, feature, description, balance_after, created_at) "
            "VALUES (?, ?, ?, '', ?, ?, ?)",
            (self.user_id, amount, tx_type, description, new_balance, now),
        )
        db.commit()
        return {"success": True, "balance_after": new_balance, "tx_id": cur.lastrowid}

    def allocate_monthly(self, amount: int) -> None:
        """Monthly tier credit allocation."""
        self._ensure()
        db = get_db()
        now = datetime.now().isoformat()
        current = self.balance()
        new_balance = current + amount

        db.execute(
            "UPDATE credit_balances SET balance = ?, monthly_allocation = ?, "
            "last_allocation_date = ? WHERE user_id = ?",
            (new_balance, amount, now, self.user_id),
        )
        db.execute(
            "INSERT INTO credit_transactions "
            "(user_id, amount, type, feature, description, balance_after, created_at) "
            "VALUES (?, ?, 'allocation', '', 'Monthly credit allocation', ?, ?)",
            (self.user_id, amount, new_balance, now),
        )
        db.commit()

    def transaction_history(self, limit: int = 50) -> list[dict]:
        """Recent transactions."""
        self._ensure()
        db = get_db()
        rows = db.execute(
            "SELECT id, amount, type, feature, description, balance_after, created_at "
            "FROM credit_transactions WHERE user_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (self.user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def requires_credits(feature: str):
    """Decorator that gates an endpoint behind a credit check.

    Checks balance, returns 402 if insufficient, auto-deducts on success.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            cost = FEATURE_COSTS.get(feature, 0)
            if cost <= 0:
                return f(*args, **kwargs)

            uid = current_user.id if current_user.is_authenticated else None
            if uid is None:
                return jsonify({"error": "Authentication required"}), 401

            store = CreditStoreDB(uid)
            if not store.has_credits(cost):
                return jsonify({
                    "error": "Insufficient credits",
                    "required": cost,
                    "balance": store.balance(),
                    "feature": feature,
                }), 402

            response = f(*args, **kwargs)

            # Auto-deduct on successful response
            if hasattr(response, "__iter__") and len(response) == 2:
                resp_obj, status = response
                if isinstance(status, int) and status >= 400:
                    return response
            store.debit(cost, feature, f"Auto-deduct for {feature}")
            return response
        return decorated
    return decorator
