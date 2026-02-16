"""
Community Analytics — Aggregate statistics across all users.
"""

from __future__ import annotations

from datetime import date, timedelta
from database import get_db


def global_stats() -> dict:
    """Return aggregate platform statistics."""
    db = get_db()

    total_users = db.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    total_questions = db.execute("SELECT COUNT(*) as c FROM grades").fetchone()["c"]
    avg_score = db.execute("SELECT AVG(percentage) as avg FROM grades").fetchone()["avg"]

    today = date.today().isoformat()
    active_today = db.execute(
        "SELECT COUNT(DISTINCT user_id) as c FROM activity_log WHERE date = ?",
        (today,),
    ).fetchone()["c"]

    # Subject distribution
    subject_rows = db.execute(
        "SELECT subject_display, COUNT(*) as cnt FROM grades GROUP BY subject_display ORDER BY cnt DESC"
    ).fetchall()
    subject_counts = {r["subject_display"]: r["cnt"] for r in subject_rows}

    return {
        "total_users": total_users,
        "total_questions": total_questions,
        "avg_score": round(avg_score, 1) if avg_score else 0,
        "active_today": active_today,
        "subject_counts": subject_counts,
    }


def trending_topics(days: int = 7) -> list[dict]:
    """Return most-practiced topics in the last N days."""
    db = get_db()
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    rows = db.execute(
        "SELECT topic, subject_display as subject, COUNT(*) as count "
        "FROM grades WHERE timestamp >= ? AND topic != '' "
        "GROUP BY topic, subject_display ORDER BY count DESC LIMIT 20",
        (cutoff,),
    ).fetchall()

    return [dict(r) for r in rows]


def difficulty_distribution() -> dict:
    """How students perform across grade levels."""
    db = get_db()
    rows = db.execute(
        "SELECT grade, COUNT(*) as count, AVG(percentage) as avg_pct "
        "FROM grades GROUP BY grade ORDER BY grade"
    ).fetchall()
    return {r["grade"]: {"count": r["count"], "avg_pct": round(r["avg_pct"], 1)} for r in rows}


def subject_popularity() -> list[dict]:
    """Active users per subject."""
    db = get_db()
    rows = db.execute(
        "SELECT subject_display, COUNT(DISTINCT user_id) as active_users, COUNT(*) as total_grades "
        "FROM grades GROUP BY subject_display ORDER BY active_users DESC"
    ).fetchall()
    return [dict(r) for r in rows]
