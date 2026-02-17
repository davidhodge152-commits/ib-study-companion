"""Predictive Analytics — Grade Prediction, Study Pattern Analysis, IB Core Bonus.

Provides weighted linear regression on grade history to predict future grades,
along with study pattern analysis from activity logs.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from database import get_db


# Official IB EE×TOK Grade Matrix (A-E × A-E → bonus points, -1 = Fail)
# Row = EE grade (A=0, B=1, ..., E=4), Col = TOK grade (A=0, ..., E=4)
_CORE_BONUS_MATRIX = [
    # TOK: A   B   C   D   E
    [3, 3, 2, 2, -1],  # EE: A
    [3, 2, 2, 1, -1],  # EE: B
    [2, 2, 1, 0, -1],  # EE: C
    [2, 1, 0, 0, -1],  # EE: D
    [-1, -1, -1, -1, -1],  # EE: E
]

_GRADE_TO_INDEX = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}


class PredictiveGradeModel:
    """Predicts IB grades using weighted linear regression on grade history."""

    MIN_DATA_POINTS = 5

    def predict_subject_grade(self, user_id: int, subject: str) -> dict | None:
        """Predict the next grade for a subject using weighted linear regression.

        Returns dict with predicted_grade, confidence_interval, trajectory,
        data_points_used, or None if insufficient data.
        """
        db = get_db()
        rows = db.execute(
            "SELECT grade, percentage, timestamp FROM grades "
            "WHERE user_id = ? AND subject_display = ? "
            "ORDER BY timestamp DESC LIMIT 30",
            (user_id, subject),
        ).fetchall()

        if len(rows) < self.MIN_DATA_POINTS:
            return None

        # Reverse to chronological order
        rows = list(reversed(rows))
        n = len(rows)

        # Weighted linear regression (more recent = higher weight)
        weights = [(i + 1) / n for i in range(n)]
        grades = [r["grade"] for r in rows]
        percentages = [r["percentage"] for r in rows]

        # Weighted means
        w_sum = sum(weights)
        x_vals = list(range(n))
        w_mean_x = sum(w * x for w, x in zip(weights, x_vals)) / w_sum
        w_mean_y = sum(w * g for w, g in zip(weights, grades)) / w_sum

        # Weighted slope and intercept
        numerator = sum(
            w * (x - w_mean_x) * (y - w_mean_y)
            for w, x, y in zip(weights, x_vals, grades)
        )
        denominator = sum(
            w * (x - w_mean_x) ** 2
            for w, x in zip(weights, x_vals)
        )

        if denominator == 0:
            predicted = w_mean_y
            slope = 0
        else:
            slope = numerator / denominator
            intercept = w_mean_y - slope * w_mean_x
            predicted = slope * n + intercept

        # Clamp to valid IB range
        predicted = max(1, min(7, predicted))

        # Confidence interval from standard deviation of residuals
        residuals = [g - (slope * x + (w_mean_y - slope * w_mean_x))
                     for x, g in zip(x_vals, grades)]
        if n > 2:
            std_dev = (sum(r ** 2 for r in residuals) / (n - 2)) ** 0.5
        else:
            std_dev = 1.0

        # Trajectory
        if slope > 0.05:
            trajectory = "improving"
        elif slope < -0.05:
            trajectory = "declining"
        else:
            trajectory = "stable"

        return {
            "predicted_grade": round(predicted, 1),
            "confidence_interval": [
                round(max(1, predicted - std_dev), 1),
                round(min(7, predicted + std_dev), 1),
            ],
            "trajectory": trajectory,
            "data_points_used": n,
            "avg_percentage": round(
                sum(percentages) / len(percentages), 1
            ),
        }

    def predict_total_ib_score(self, user_id: int) -> dict:
        """Aggregate per-subject predictions into total IB score prediction."""
        db = get_db()
        subjects = db.execute(
            "SELECT DISTINCT subject_display FROM grades WHERE user_id = ?",
            (user_id,),
        ).fetchall()

        subject_predictions = {}
        total = 0
        count = 0

        for row in subjects:
            subj = row["subject_display"]
            pred = self.predict_subject_grade(user_id, subj)
            if pred:
                subject_predictions[subj] = pred
                total += pred["predicted_grade"]
                count += 1

        # Try to add core bonus
        core_bonus = self._calculate_core_bonus(user_id)

        return {
            "subject_predictions": subject_predictions,
            "predicted_subject_total": round(total, 1),
            "core_bonus": core_bonus,
            "predicted_total": round(total + max(0, core_bonus), 1),
            "subjects_with_data": count,
        }

    def _calculate_core_bonus(self, user_id: int) -> int:
        """Calculate IB core bonus from EE and TOK grades using official matrix."""
        db = get_db()

        # Get EE predicted grade (A-E from ee_grade or predicted)
        ee_grade = None
        try:
            ee_row = db.execute(
                "SELECT subject FROM extended_essays WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if ee_row:
                # Use most recent EE-related grade if available
                g_row = db.execute(
                    "SELECT grade FROM grades WHERE user_id = ? AND "
                    "(subject_display LIKE '%extended%' OR subject_display LIKE '%ee%') "
                    "ORDER BY timestamp DESC LIMIT 1",
                    (user_id,),
                ).fetchone()
                if g_row:
                    # Map IB 1-7 to A-E (7=A, 6=A, 5=B, 4=C, 3=D, 2=E, 1=E)
                    grade_map = {7: "A", 6: "A", 5: "B", 4: "C", 3: "D", 2: "E", 1: "E"}
                    ee_grade = grade_map.get(g_row["grade"], "C")
        except Exception:
            pass

        # Get TOK predicted grade
        tok_grade = None
        try:
            tok_row = db.execute(
                "SELECT essay_title FROM tok_progress WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if tok_row:
                g_row = db.execute(
                    "SELECT grade FROM grades WHERE user_id = ? AND "
                    "(subject_display LIKE '%tok%' OR subject_display LIKE '%theory%') "
                    "ORDER BY timestamp DESC LIMIT 1",
                    (user_id,),
                ).fetchone()
                if g_row:
                    grade_map = {7: "A", 6: "A", 5: "B", 4: "C", 3: "D", 2: "E", 1: "E"}
                    tok_grade = grade_map.get(g_row["grade"], "C")
        except Exception:
            pass

        if ee_grade is None or tok_grade is None:
            return 0  # Can't calculate without both

        ee_idx = _GRADE_TO_INDEX.get(ee_grade, 2)
        tok_idx = _GRADE_TO_INDEX.get(tok_grade, 2)
        bonus = _CORE_BONUS_MATRIX[ee_idx][tok_idx]

        return bonus  # -1 means failing condition

    def study_pattern_analysis(self, user_id: int) -> dict:
        """Analyze study patterns from activity log."""
        db = get_db()
        cutoff = (datetime.now() - timedelta(days=30)).isoformat()

        rows = db.execute(
            "SELECT date, subject, questions_attempted, duration_minutes, timestamp "
            "FROM activity_log WHERE user_id = ? AND date >= ? "
            "ORDER BY date",
            (user_id, cutoff[:10]),
        ).fetchall()

        if not rows:
            return {
                "best_hour": None,
                "best_day": None,
                "avg_session_minutes": 0,
                "consistency_score": 0.0,
                "total_sessions": 0,
                "total_questions": 0,
            }

        # Analyze timestamps for best study hour
        hour_counts: dict[int, int] = {}
        day_counts: dict[str, int] = {}
        durations = []
        dates_studied: set[str] = set()

        for r in rows:
            ts = r["timestamp"] or r["date"]
            try:
                dt = datetime.fromisoformat(ts)
                hour_counts[dt.hour] = hour_counts.get(dt.hour, 0) + 1
                day_name = dt.strftime("%A")
                day_counts[day_name] = day_counts.get(day_name, 0) + 1
            except (ValueError, TypeError):
                pass

            if r["duration_minutes"]:
                durations.append(r["duration_minutes"])
            dates_studied.add(r["date"])

        best_hour = max(hour_counts, key=hour_counts.get) if hour_counts else None
        best_day = max(day_counts, key=day_counts.get) if day_counts else None

        # Consistency: days studied / total days in period
        total_days = 30
        consistency = len(dates_studied) / total_days

        return {
            "best_hour": best_hour,
            "best_day": best_day,
            "avg_session_minutes": round(
                sum(durations) / len(durations), 1
            ) if durations else 0,
            "consistency_score": round(consistency, 2),
            "total_sessions": len(rows),
            "total_questions": sum(r["questions_attempted"] for r in rows),
        }
