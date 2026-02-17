"""
Data Pipeline — Daily analytics aggregation and anonymized export.

Functions:
  - aggregate_daily_analytics(app): Compute daily stats, upsert into daily_aggregates.
  - export_anonymized_analytics(app): Strip PII, hash user_ids, return JSON-safe dict.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta


def aggregate_daily_analytics(app) -> dict:
    """Run daily aggregation: active users, questions graded, avg score, etc.

    Upserts rows into daily_aggregates table. Returns summary dict.
    """
    with app.app_context():
        from database import get_db
        db = get_db()

        today = date.today().isoformat()

        # Active users today
        active_users = db.execute(
            "SELECT COUNT(DISTINCT user_id) as c FROM activity_log WHERE date = ?",
            (today,),
        ).fetchone()["c"]

        # Questions graded today
        questions_graded = db.execute(
            "SELECT COUNT(*) as c FROM grades WHERE timestamp LIKE ?",
            (f"{today}%",),
        ).fetchone()["c"]

        # Average score today
        avg_row = db.execute(
            "SELECT AVG(percentage) as avg FROM grades WHERE timestamp LIKE ?",
            (f"{today}%",),
        ).fetchone()
        avg_score = round(avg_row["avg"], 1) if avg_row["avg"] else 0

        # Subject distribution today
        subject_rows = db.execute(
            "SELECT subject_display, COUNT(*) as cnt FROM grades "
            "WHERE timestamp LIKE ? GROUP BY subject_display",
            (f"{today}%",),
        ).fetchall()
        subject_breakdown = {r["subject_display"]: r["cnt"] for r in subject_rows}

        # AI cost totals today (from agent_interactions)
        cost_row = db.execute(
            "SELECT SUM(cost_estimate_usd) as total_cost, COUNT(*) as calls "
            "FROM agent_interactions WHERE created_at LIKE ?",
            (f"{today}%",),
        ).fetchone()
        ai_cost = round(cost_row["total_cost"], 4) if cost_row["total_cost"] else 0
        ai_calls = cost_row["calls"] if cost_row["calls"] else 0

        now = datetime.now().isoformat()

        # Upsert metrics
        metrics = {
            "active_users": active_users,
            "questions_graded": questions_graded,
            "avg_score": avg_score,
            "ai_cost_usd": ai_cost,
            "ai_calls": ai_calls,
        }

        for metric, value in metrics.items():
            breakdown = json.dumps(subject_breakdown) if metric == "questions_graded" else "{}"
            db.execute(
                "INSERT INTO daily_aggregates (date, metric, value, breakdown, created_at) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(date, metric) DO UPDATE SET value = ?, breakdown = ?, created_at = ?",
                (today, metric, value, breakdown, now, value, breakdown, now),
            )

        db.commit()

        return {
            "date": today,
            "active_users": active_users,
            "questions_graded": questions_graded,
            "avg_score": avg_score,
            "ai_cost_usd": ai_cost,
            "ai_calls": ai_calls,
            "subject_breakdown": subject_breakdown,
        }


def export_anonymized_analytics(app) -> dict:
    """Export anonymized analytics data, stripping PII and hashing user_ids.

    Returns a JSON-serializable dict with aggregate stats.
    """
    with app.app_context():
        from database import get_db
        db = get_db()

        # Grade distribution (anonymized)
        grade_dist = db.execute(
            "SELECT grade, COUNT(*) as count, AVG(percentage) as avg_pct "
            "FROM grades GROUP BY grade ORDER BY grade"
        ).fetchall()

        # Activity patterns (anonymized)
        activity_rows = db.execute(
            "SELECT date, COUNT(*) as sessions, SUM(questions_attempted) as questions, "
            "AVG(duration_minutes) as avg_duration "
            "FROM activity_log "
            "WHERE date >= ? "
            "GROUP BY date ORDER BY date",
            ((date.today() - timedelta(days=30)).isoformat(),),
        ).fetchall()

        # Feature usage — which agents are most used
        agent_rows = db.execute(
            "SELECT agent, COUNT(*) as calls, AVG(latency_ms) as avg_latency "
            "FROM agent_interactions "
            "WHERE created_at >= ? "
            "GROUP BY agent ORDER BY calls DESC",
            ((date.today() - timedelta(days=30)).isoformat(),),
        ).fetchall()

        # Conversion funnel: registered → completed onboarding → has grades → active this week
        total_users = db.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
        with_subjects = db.execute(
            "SELECT COUNT(DISTINCT user_id) as c FROM user_subjects"
        ).fetchone()["c"]
        with_grades = db.execute(
            "SELECT COUNT(DISTINCT user_id) as c FROM grades"
        ).fetchone()["c"]
        week_ago = (date.today() - timedelta(days=7)).isoformat()
        active_week = db.execute(
            "SELECT COUNT(DISTINCT user_id) as c FROM grades WHERE timestamp >= ?",
            (week_ago,),
        ).fetchone()["c"]

        # Per-user aggregate (hashed IDs, no names/emails)
        user_aggregates = []
        user_rows = db.execute(
            "SELECT user_id, COUNT(*) as total_grades, AVG(percentage) as avg_pct, "
            "MAX(timestamp) as last_active "
            "FROM grades GROUP BY user_id"
        ).fetchall()
        for r in user_rows:
            hashed_id = hashlib.sha256(str(r["user_id"]).encode()).hexdigest()[:12]
            user_aggregates.append({
                "anon_id": hashed_id,
                "total_grades": r["total_grades"],
                "avg_pct": round(r["avg_pct"], 1) if r["avg_pct"] else 0,
                "last_active": r["last_active"],
            })

        return {
            "export_date": date.today().isoformat(),
            "grade_distribution": [
                {"grade": r["grade"], "count": r["count"],
                 "avg_pct": round(r["avg_pct"], 1) if r["avg_pct"] else 0}
                for r in grade_dist
            ],
            "daily_activity": [
                {"date": r["date"], "sessions": r["sessions"],
                 "questions": r["questions"],
                 "avg_duration": round(r["avg_duration"], 1) if r["avg_duration"] else 0}
                for r in activity_rows
            ],
            "agent_usage": [
                {"agent": r["agent"], "calls": r["calls"],
                 "avg_latency_ms": round(r["avg_latency"], 0) if r["avg_latency"] else 0}
                for r in agent_rows
            ],
            "conversion_funnel": {
                "registered": total_users,
                "onboarded": with_subjects,
                "has_grades": with_grades,
                "active_this_week": active_week,
            },
            "user_aggregates": user_aggregates,
        }
