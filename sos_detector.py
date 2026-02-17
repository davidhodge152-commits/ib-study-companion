"""SOS Detection & Micro-Tutoring Pipeline.

Monitors student performance to detect struggling patterns,
creates SOS alerts, and manages tutoring request workflow.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from database import get_db


class SOSDetector:
    """Detects students struggling on specific topics and manages tutoring requests."""

    FAILURE_THRESHOLD = 3
    LOOKBACK_DAYS = 14
    LOW_PERCENTAGE_THRESHOLD = 40

    def __init__(self, user_id: int):
        self.user_id = user_id

    def check_for_sos(self) -> list[dict]:
        """Check recent grades for SOS-worthy failure patterns.

        Groups by (subject, topic) where avg percentage < 40% and
        failure count >= 3 within the last 14 days.
        Returns list of active SOS alerts.
        """
        db = get_db()
        cutoff = (datetime.now() - timedelta(days=self.LOOKBACK_DAYS)).isoformat()

        rows = db.execute(
            "SELECT subject, topic, COUNT(*) as fail_count, "
            "AVG(percentage) as avg_pct "
            "FROM grades "
            "WHERE user_id = ? AND percentage < ? AND timestamp >= ? "
            "AND topic != '' "
            "GROUP BY subject, topic "
            "HAVING fail_count >= ?",
            (self.user_id, self.LOW_PERCENTAGE_THRESHOLD, cutoff,
             self.FAILURE_THRESHOLD),
        ).fetchall()

        alerts = []
        now = datetime.now().isoformat()

        for r in rows:
            # Check if alert already exists
            existing = db.execute(
                "SELECT id, status FROM sos_alerts "
                "WHERE user_id = ? AND subject = ? AND topic = ? AND status = 'active'",
                (self.user_id, r["subject"], r["topic"]),
            ).fetchone()

            if existing:
                # Update existing alert
                db.execute(
                    "UPDATE sos_alerts SET failure_count = ?, avg_percentage = ? "
                    "WHERE id = ?",
                    (r["fail_count"], r["avg_pct"], existing["id"]),
                )
                db.commit()
                alerts.append({
                    "id": existing["id"],
                    "subject": r["subject"],
                    "topic": r["topic"],
                    "failure_count": r["fail_count"],
                    "avg_percentage": round(r["avg_pct"], 1),
                    "status": "active",
                })
            else:
                # Build context summary from misconceptions
                context = self._build_context_summary(r["subject"], r["topic"])

                cur = db.execute(
                    "INSERT INTO sos_alerts "
                    "(user_id, subject, topic, failure_count, avg_percentage, "
                    "status, context_summary, created_at) "
                    "VALUES (?, ?, ?, ?, ?, 'active', ?, ?)",
                    (self.user_id, r["subject"], r["topic"],
                     r["fail_count"], r["avg_pct"], context, now),
                )
                db.commit()

                alert_id = cur.lastrowid
                alerts.append({
                    "id": alert_id,
                    "subject": r["subject"],
                    "topic": r["topic"],
                    "failure_count": r["fail_count"],
                    "avg_percentage": round(r["avg_pct"], 1),
                    "status": "active",
                })

                # Create notification
                self._notify_sos(alert_id, r["subject"], r["topic"])

        return alerts

    def _build_context_summary(self, subject: str, topic: str) -> str:
        """Build a context summary from recent failed attempts."""
        db = get_db()
        cutoff = (datetime.now() - timedelta(days=self.LOOKBACK_DAYS)).isoformat()
        rows = db.execute(
            "SELECT improvements FROM grades "
            "WHERE user_id = ? AND subject = ? AND topic = ? "
            "AND percentage < ? AND timestamp >= ? "
            "ORDER BY timestamp DESC LIMIT 5",
            (self.user_id, subject, topic,
             self.LOW_PERCENTAGE_THRESHOLD, cutoff),
        ).fetchall()

        issues = []
        for r in rows:
            try:
                improvements = json.loads(r["improvements"])
                issues.extend(improvements[:2])
            except (json.JSONDecodeError, TypeError):
                pass

        return "; ".join(issues[:5]) if issues else "Multiple failed attempts"

    def _notify_sos(self, alert_id: int, subject: str, topic: str) -> None:
        """Create an SOS notification for the student."""
        try:
            from db_stores import NotificationStoreDB
            from profile import Notification
            import secrets

            notif = NotificationStoreDB(self.user_id)
            notif.add(Notification(
                id=secrets.token_hex(8),
                type="sos_alert",
                title=f"Struggling with {topic} in {subject}?",
                body=f"You've had {self.FAILURE_THRESHOLD}+ low scores on this topic. "
                     "Consider requesting a tutoring session.",
                action_url=f"/sos?alert={alert_id}",
            ))
        except Exception:
            pass

    def active_alerts(self) -> list[dict]:
        """Get all active SOS alerts for this user."""
        db = get_db()
        rows = db.execute(
            "SELECT id, subject, topic, failure_count, avg_percentage, "
            "context_summary, created_at "
            "FROM sos_alerts WHERE user_id = ? AND status = 'active' "
            "ORDER BY created_at DESC",
            (self.user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def build_tutor_context(self, alert_id: int) -> dict:
        """Build a pre-loaded context packet for a human tutor."""
        db = get_db()
        alert = db.execute(
            "SELECT * FROM sos_alerts WHERE id = ? AND user_id = ?",
            (alert_id, self.user_id),
        ).fetchone()
        if not alert:
            return {}

        # Get recent failed attempts
        cutoff = (datetime.now() - timedelta(days=self.LOOKBACK_DAYS)).isoformat()
        attempts = db.execute(
            "SELECT percentage, grade, strengths, improvements, timestamp "
            "FROM grades "
            "WHERE user_id = ? AND subject = ? AND topic = ? AND timestamp >= ? "
            "ORDER BY timestamp DESC LIMIT 10",
            (self.user_id, alert["subject"], alert["topic"], cutoff),
        ).fetchall()

        error_history = []
        for a in attempts:
            entry = dict(a)
            for key in ("strengths", "improvements"):
                try:
                    entry[key] = json.loads(entry[key])
                except (json.JSONDecodeError, TypeError):
                    pass
            error_history.append(entry)

        # Get theta from adaptive system
        theta = 0.0
        try:
            from db_stores import StudentAbilityStoreDB
            ability = StudentAbilityStoreDB(self.user_id).get_theta(
                alert["subject"], alert["topic"],
            )
            theta = ability.get("theta", 0.0)
        except Exception:
            pass

        return {
            "alert_id": alert_id,
            "subject": alert["subject"],
            "topic": alert["topic"],
            "theta": theta,
            "failure_count": alert["failure_count"],
            "avg_percentage": alert["avg_percentage"],
            "context_summary": alert["context_summary"],
            "error_history": error_history,
        }

    def request_session(self, alert_id: int) -> dict:
        """Create a tutoring request from an SOS alert."""
        context = self.build_tutor_context(alert_id)
        if not context:
            return {"success": False, "error": "Alert not found"}

        db = get_db()
        now = datetime.now().isoformat()

        # Deduct credits
        from credit_store import CreditStoreDB, FEATURE_COSTS
        store = CreditStoreDB(self.user_id)
        cost = FEATURE_COSTS.get("oral_practice", 50)
        result = store.debit(cost, "tutoring_session", f"Tutoring: {context['topic']}")
        if not result["success"]:
            return {"success": False, "error": "Insufficient credits",
                    "required": cost, "balance": result["balance_after"]}

        cur = db.execute(
            "INSERT INTO tutoring_requests "
            "(user_id, subject, topic, error_history, context_summary, "
            "mastery_state, theta, status, credits_charged, created_at) "
            "VALUES (?, ?, ?, ?, ?, '', ?, 'pending', ?, ?)",
            (self.user_id, context["subject"], context["topic"],
             json.dumps(context["error_history"]), context["context_summary"],
             context["theta"], cost, now),
        )
        db.commit()

        return {
            "success": True,
            "request_id": cur.lastrowid,
            "credits_charged": cost,
        }

    @staticmethod
    def get_tutor_request(request_id: int) -> dict | None:
        """Get a tutoring request by ID (for tutors)."""
        db = get_db()
        row = db.execute(
            "SELECT * FROM tutoring_requests WHERE id = ?",
            (request_id,),
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        try:
            result["error_history"] = json.loads(result["error_history"])
        except (json.JSONDecodeError, TypeError):
            pass
        return result

    @staticmethod
    def complete_session(request_id: int, tutor_id: int) -> None:
        """Mark a tutoring session as completed."""
        db = get_db()
        now = datetime.now().isoformat()
        db.execute(
            "UPDATE tutoring_requests SET status = 'completed', "
            "tutor_id = ?, completed_at = ? WHERE id = ?",
            (tutor_id, now, request_id),
        )
        # Resolve the related SOS alert
        req = db.execute(
            "SELECT user_id, subject, topic FROM tutoring_requests WHERE id = ?",
            (request_id,),
        ).fetchone()
        if req:
            db.execute(
                "UPDATE sos_alerts SET status = 'resolved', resolved_at = ? "
                "WHERE user_id = ? AND subject = ? AND topic = ? AND status = 'active'",
                (now, req["user_id"], req["subject"], req["topic"]),
            )
        db.commit()
