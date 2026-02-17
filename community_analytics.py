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


def peer_percentile(user_id: int, subject: str) -> dict:
    """Calculate a user's percentile rank among peers in a subject.

    Requires at least 10 other users for privacy. Returns dict with
    percentile, sample_size, avg_peer_score, your_avg.
    """
    db = get_db()

    # Get user's average percentage in this subject
    user_row = db.execute(
        "SELECT AVG(percentage) as avg_pct, COUNT(*) as cnt "
        "FROM grades WHERE user_id = ? AND subject_display = ?",
        (user_id, subject),
    ).fetchone()

    if not user_row or not user_row["avg_pct"]:
        return {"error": "No grades found for this subject"}

    user_avg = user_row["avg_pct"]

    # Get all other users' averages in this subject
    peer_rows = db.execute(
        "SELECT user_id, AVG(percentage) as avg_pct "
        "FROM grades WHERE subject_display = ? AND user_id != ? "
        "GROUP BY user_id",
        (subject, user_id),
    ).fetchall()

    if len(peer_rows) < 10:
        return {
            "error": "Insufficient peer data",
            "sample_size": len(peer_rows),
            "min_required": 10,
        }

    peer_avgs = [r["avg_pct"] for r in peer_rows]
    below_count = sum(1 for a in peer_avgs if a < user_avg)
    total = len(peer_avgs)
    percentile = round((below_count / total) * 100, 1)

    return {
        "percentile": percentile,
        "sample_size": total,
        "avg_peer_score": round(sum(peer_avgs) / total, 1),
        "your_avg": round(user_avg, 1),
        "your_grades_count": user_row["cnt"],
    }
