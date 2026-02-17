"""Enhanced Parent Portal — Traffic-Light Dashboard.

Provides parent-facing analytics including traffic-light subject overview,
SOS highlights, weekly digest, and actionable recommendations.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from database import get_db


class ParentAnalytics:
    """Analytics engine for the parent portal."""

    def __init__(self, user_id: int):
        self.user_id = user_id

    def traffic_light(self) -> dict:
        """Traffic-light status per subject.

        Compares predicted grade (from recent grade averages) to target grade.
        Green: on_track (gap <= 0), Yellow: watch (gap = 1), Red: action (gap >= 2)
        """
        db = get_db()

        # Get student's subjects and targets
        subjects_rows = db.execute(
            "SELECT name, level, target_grade FROM user_subjects WHERE user_id = ?",
            (self.user_id,),
        ).fetchall()

        if not subjects_rows:
            return {"subjects": []}

        results = []
        for s in subjects_rows:
            subject_key = s["name"].lower().split(":")[0].strip().replace(" ", "_")
            target = s["target_grade"]

            # Get last 20 grades for this subject
            grades = db.execute(
                "SELECT grade, percentage, timestamp FROM grades "
                "WHERE user_id = ? AND subject = ? "
                "ORDER BY timestamp DESC LIMIT 20",
                (self.user_id, subject_key),
            ).fetchall()

            if not grades:
                results.append({
                    "name": s["name"], "level": s["level"],
                    "predicted": 0, "target": target,
                    "gap": target, "status": "no_data", "trend": "none",
                })
                continue

            # Predicted = average of last 10 grades
            recent_10 = [g["grade"] for g in grades[:10]]
            predicted = round(sum(recent_10) / len(recent_10)) if recent_10 else 0

            # Trend: compare last 10 to previous 10
            prev_10 = [g["grade"] for g in grades[10:20]]
            if prev_10:
                prev_avg = sum(prev_10) / len(prev_10)
                recent_avg = sum(recent_10) / len(recent_10)
                if recent_avg > prev_avg + 0.3:
                    trend = "improving"
                elif recent_avg < prev_avg - 0.3:
                    trend = "declining"
                else:
                    trend = "stable"
            else:
                trend = "insufficient_data"

            gap = target - predicted
            if gap <= 0:
                status = "on_track"
            elif gap == 1:
                status = "watch"
            else:
                status = "action"

            results.append({
                "name": s["name"], "level": s["level"],
                "predicted": predicted, "target": target,
                "gap": gap, "status": status, "trend": trend,
            })

        return {"subjects": results}

    def sos_highlights(self) -> list[dict]:
        """Active SOS alerts formatted for parent consumption."""
        db = get_db()
        rows = db.execute(
            "SELECT subject, topic, failure_count, avg_percentage "
            "FROM sos_alerts WHERE user_id = ? AND status = 'active' "
            "ORDER BY failure_count DESC",
            (self.user_id,),
        ).fetchall()

        highlights = []
        for r in rows:
            recommendation = (
                f"Your child has scored below 40% on {r['topic']} "
                f"({r['failure_count']} times). Consider encouraging extra "
                f"practice or a tutoring session."
            )
            highlights.append({
                "subject": r["subject"],
                "topic": r["topic"],
                "failure_count": r["failure_count"],
                "avg_percentage": round(r["avg_percentage"], 1),
                "recommendation": recommendation,
            })
        return highlights

    def weekly_digest(self) -> dict:
        """Weekly summary of student activity for parents."""
        db = get_db()
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()

        # Questions attempted this week
        activity = db.execute(
            "SELECT SUM(questions_attempted) as total_q, "
            "SUM(duration_minutes) as total_mins, "
            "COUNT(DISTINCT date) as active_days "
            "FROM activity_log WHERE user_id = ? AND timestamp >= ?",
            (self.user_id, week_ago),
        ).fetchone()

        questions = activity["total_q"] or 0 if activity else 0
        study_mins = activity["total_mins"] or 0 if activity else 0
        active_days = activity["active_days"] or 0 if activity else 0

        # Current streak
        streak = 0
        try:
            from db_stores import GamificationProfileDB
            gam = GamificationProfileDB(self.user_id)
            streak = gam.current_streak
        except Exception:
            pass

        # New badges this week
        new_badges = []
        try:
            from db_stores import GamificationProfileDB
            gam = GamificationProfileDB(self.user_id)
            for badge_id, data in gam.badges.items():
                if isinstance(data, dict) and data.get("earned_at", "") >= week_ago:
                    from profile import BADGE_DEFINITIONS
                    badge_def = BADGE_DEFINITIONS.get(badge_id, {})
                    new_badges.append(badge_def.get("name", badge_id))
        except Exception:
            pass

        # Grade average this week
        grades = db.execute(
            "SELECT AVG(grade) as avg_grade, AVG(percentage) as avg_pct "
            "FROM grades WHERE user_id = ? AND timestamp >= ?",
            (self.user_id, week_ago),
        ).fetchone()

        avg_grade = round(grades["avg_grade"], 1) if grades and grades["avg_grade"] else 0
        avg_pct = round(grades["avg_pct"], 1) if grades and grades["avg_pct"] else 0

        return {
            "questions_attempted": questions,
            "study_minutes": study_mins,
            "active_days": active_days,
            "streak": streak,
            "new_badges": new_badges,
            "avg_grade": avg_grade,
            "avg_percentage": avg_pct,
        }

    def action_items(self) -> list[str]:
        """Top 3 actionable recommendations for parents."""
        items = []

        # Get student name
        db = get_db()
        user = db.execute(
            "SELECT name FROM users WHERE id = ?", (self.user_id,),
        ).fetchone()
        name = user["name"].split()[0] if user else "Your child"

        # Check SOS alerts
        sos = self.sos_highlights()
        if sos:
            top = sos[0]
            items.append(
                f"{name} should focus on {top['topic']} in {top['subject']} this week"
            )

        # Check traffic light for red subjects
        tl = self.traffic_light()
        for s in tl.get("subjects", []):
            if s["status"] == "action" and len(items) < 3:
                items.append(
                    f"Encourage {name} to practice {s['name']} "
                    f"(currently predicted {s['predicted']}, target {s['target']})"
                )

        # Check upcoming deadlines
        try:
            deadlines = db.execute(
                "SELECT title, subject, due_date FROM study_deadlines "
                "WHERE user_id = ? AND completed = 0 AND due_date >= ? "
                "ORDER BY due_date LIMIT 3",
                (self.user_id, datetime.now().isoformat()),
            ).fetchall()
            for d in deadlines:
                if len(items) < 3:
                    items.append(
                        f"Encourage {name} to complete '{d['title']}' by {d['due_date'][:10]}"
                    )
        except Exception:
            pass

        # Default if nothing flagged
        if not items:
            items.append(f"{name} is on track — encourage consistent daily study")

        return items[:3]
