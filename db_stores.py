"""
DB-backed store classes for IB Study Companion.

Each class mirrors the public API of the original JSON-backed stores in profile.py
and lifecycle.py, but reads/writes from SQLite instead of flat JSON files.
"""

from __future__ import annotations

import json
import math
import secrets
from dataclasses import dataclass, field, asdict
from datetime import datetime, date, timedelta
from typing import Optional

from database import get_db

# Re-export dataclasses used by app.py (unchanged from profile.py)
from profile import (
    SubjectEntry,
    GradeDetailEntry,
    ActivityEntry,
    ReviewItem,
    StudyTask,
    DailyPlan,
    Flashcard,
    MisconceptionEntry,
    MockExamReport,
    Notification,
    SharedQuestionSet,
    TopicAttempt,
    TopicProgress,
    MISCONCEPTION_PATTERNS,
    BADGE_DEFINITIONS,
    XP_AWARDS,
)
from lifecycle import (
    Milestone,
    ExtendedEssay,
    InternalAssessment,
    CASReflection,
    TOKProgress,
    CAS_LEARNING_OUTCOMES,
)


# ── Student Profile ──────────────────────────────────────────────────


class StudentProfileDB:
    """DB-backed StudentProfile matching the original public API."""

    def __init__(self, user_id: int = 1):
        self.user_id = user_id
        self._row = None
        self._subjects: list[SubjectEntry] = []
        self._load()

    def _load(self):
        db = get_db()
        self._row = db.execute("SELECT * FROM users WHERE id = ?", (self.user_id,)).fetchone()
        if self._row:
            rows = db.execute(
                "SELECT name, level, target_grade FROM user_subjects WHERE user_id = ? ORDER BY id",
                (self.user_id,),
            ).fetchall()
            self._subjects = [SubjectEntry(name=r["name"], level=r["level"], target_grade=r["target_grade"]) for r in rows]

    @property
    def name(self) -> str:
        return self._row["name"] if self._row else ""

    @property
    def subjects(self) -> list[SubjectEntry]:
        return self._subjects

    @property
    def exam_session(self) -> str:
        return self._row["exam_session"] if self._row else ""

    @property
    def target_total_points(self) -> int:
        return self._row["target_total_points"] if self._row else 35

    @property
    def created_at(self) -> str:
        return self._row["created_at"] if self._row else ""

    def to_dict(self) -> dict:
        """Return a JSON-serializable dict for template rendering."""
        return {
            "name": self.name,
            "exam_session": self.exam_session,
            "target_total_points": self.target_total_points,
            "subjects": [
                {"name": s.name, "level": s.level, "target_grade": s.target_grade}
                for s in self.subjects
            ],
        }

    def save(self) -> None:
        db = get_db()
        db.execute(
            "UPDATE users SET name=?, exam_session=?, target_total_points=? WHERE id=?",
            (self.name, self.exam_session, self.target_total_points, self.user_id),
        )
        db.execute("DELETE FROM user_subjects WHERE user_id=?", (self.user_id,))
        for s in self._subjects:
            db.execute(
                "INSERT INTO user_subjects (user_id, name, level, target_grade) VALUES (?, ?, ?, ?)",
                (self.user_id, s.name, s.level, s.target_grade),
            )
        db.commit()

    def save_fields(self, *, name=None, exam_session=None, target_total_points=None, subjects=None) -> None:
        """Update specific fields and save."""
        db = get_db()
        if name is not None or exam_session is not None or target_total_points is not None:
            sets = []
            vals = []
            if name is not None:
                sets.append("name=?")
                vals.append(name)
            if exam_session is not None:
                sets.append("exam_session=?")
                vals.append(exam_session)
            if target_total_points is not None:
                sets.append("target_total_points=?")
                vals.append(target_total_points)
            vals.append(self.user_id)
            db.execute(f"UPDATE users SET {', '.join(sets)} WHERE id=?", vals)

        if subjects is not None:
            self._subjects = subjects
            db.execute("DELETE FROM user_subjects WHERE user_id=?", (self.user_id,))
            for s in subjects:
                db.execute(
                    "INSERT INTO user_subjects (user_id, name, level, target_grade) VALUES (?, ?, ?, ?)",
                    (self.user_id, s.name, s.level, s.target_grade),
                )
        db.commit()
        self._load()

    @staticmethod
    def load(user_id: int = 1) -> Optional[StudentProfileDB]:
        db = get_db()
        row = db.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            return None
        return StudentProfileDB(user_id)

    @staticmethod
    def exists(user_id: int = 1) -> bool:
        db = get_db()
        return db.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is not None

    @staticmethod
    def create(name: str, subjects: list[SubjectEntry], exam_session: str,
               target_total_points: int = 35, email: str = "", password_hash: str = "") -> StudentProfileDB:
        """Create a new user profile."""
        db = get_db()
        now = datetime.now().isoformat()
        cur = db.execute(
            "INSERT INTO users (name, email, password_hash, exam_session, target_total_points, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, email, password_hash, exam_session, target_total_points, now),
        )
        user_id = cur.lastrowid
        for s in subjects:
            db.execute(
                "INSERT INTO user_subjects (user_id, name, level, target_grade) VALUES (?, ?, ?, ?)",
                (user_id, s.name, s.level, s.target_grade),
            )
        # Create gamification row
        db.execute("INSERT OR IGNORE INTO gamification (user_id) VALUES (?)", (user_id,))
        db.commit()
        return StudentProfileDB(user_id)

    def subject_key(self, name: str) -> str:
        return name.lower().split(":")[0].strip().replace(" ", "_")

    def exam_countdown(self) -> dict:
        today = date.today()
        try:
            parts = self.exam_session.split()
            month_str = parts[0].lower()
            year = int(parts[1])
            exam_date = date(year, 5, 1) if month_str.startswith("may") else date(year, 11, 1)
        except (ValueError, IndexError):
            year = today.year if today.month < 5 else today.year + 1
            exam_date = date(year, 5, 1)
        days = max(0, (exam_date - today).days)
        if days > 120:
            urgency = "calm"
        elif days > 60:
            urgency = "focused"
        elif days > 21:
            urgency = "urgent"
        else:
            urgency = "critical"
        return {"days": days, "urgency": urgency, "exam_date": exam_date.isoformat()}

    def compute_gaps(self, grade_log: GradeDetailLogDB) -> list[dict]:
        subject_stats = grade_log.subject_stats()
        gaps = []
        for s in self._subjects:
            stats = subject_stats.get(s.name, None)
            if stats and stats["count"] > 0:
                predicted = round(stats["avg_grade"])
                gap = s.target_grade - predicted
                status = "on_track" if gap <= 0 else ("close" if gap == 1 else "behind")
            else:
                predicted = 0
                gap = 0
                status = "no_data"
            gaps.append({
                "subject": s.name, "level": s.level, "target": s.target_grade,
                "predicted": predicted, "gap": gap, "status": status,
            })
        gaps.sort(key=lambda g: (-g["gap"] if g["status"] != "no_data" else -999))
        return gaps

    def compute_predicted_total(self, grade_log: GradeDetailLogDB) -> int:
        subject_stats = grade_log.subject_stats()
        total = 0
        for s in self._subjects:
            stats = subject_stats.get(s.name, None)
            if stats and stats["count"] > 0:
                total += round(stats["avg_grade"])
            else:
                total += s.target_grade
        return total


# ── Grade Detail Log ─────────────────────────────────────────────────


class GradeDetailLogDB:
    """DB-backed GradeDetailLog."""

    def __init__(self, user_id: int = 1):
        self.user_id = user_id

    @property
    def entries(self) -> list[GradeDetailEntry]:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM grades WHERE user_id = ? ORDER BY id", (self.user_id,)
        ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def add(self, entry: GradeDetailEntry) -> None:
        db = get_db()
        db.execute(
            "INSERT INTO grades (user_id, subject, subject_display, level, command_term, "
            "grade, percentage, mark_earned, mark_total, strengths, improvements, "
            "examiner_tip, topic, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (self.user_id, entry.subject, entry.subject_display, entry.level,
             entry.command_term, entry.grade, entry.percentage, entry.mark_earned,
             entry.mark_total, json.dumps(entry.strengths), json.dumps(entry.improvements),
             entry.examiner_tip, entry.topic, entry.timestamp),
        )
        db.commit()

    def by_subject(self, subject_display: str) -> list[GradeDetailEntry]:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM grades WHERE user_id = ? AND subject_display = ? ORDER BY id",
            (self.user_id, subject_display),
        ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def by_command_term(self, command_term: str) -> list[GradeDetailEntry]:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM grades WHERE user_id = ? AND LOWER(command_term) = LOWER(?) ORDER BY id",
            (self.user_id, command_term),
        ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def command_term_stats(self) -> dict:
        db = get_db()
        rows = db.execute(
            "SELECT command_term, COUNT(*) as cnt, "
            "ROUND(AVG(grade), 1) as avg_grade, ROUND(AVG(percentage), 1) as avg_pct "
            "FROM grades WHERE user_id = ? GROUP BY command_term",
            (self.user_id,),
        ).fetchall()
        stats = {}
        for r in rows:
            ct = r["command_term"] or "Unknown"
            stats[ct] = {"count": r["cnt"], "avg_grade": r["avg_grade"] or 0, "avg_percentage": r["avg_pct"] or 0}
        return stats

    def subject_stats(self) -> dict:
        db = get_db()
        rows = db.execute(
            "SELECT subject_display, COUNT(*) as cnt, "
            "ROUND(AVG(grade), 1) as avg_grade, ROUND(AVG(percentage), 1) as avg_pct "
            "FROM grades WHERE user_id = ? GROUP BY subject_display",
            (self.user_id,),
        ).fetchall()
        stats = {}
        for r in rows:
            stats[r["subject_display"]] = {
                "count": r["cnt"], "avg_grade": r["avg_grade"] or 0, "avg_percentage": r["avg_pct"] or 0,
            }
        return stats

    def recent(self, n: int = 5) -> list[GradeDetailEntry]:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM grades WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (self.user_id, n),
        ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def _row_to_entry(self, r) -> GradeDetailEntry:
        return GradeDetailEntry(
            subject=r["subject"], subject_display=r["subject_display"],
            level=r["level"], command_term=r["command_term"],
            grade=r["grade"], percentage=r["percentage"],
            mark_earned=r["mark_earned"], mark_total=r["mark_total"],
            strengths=json.loads(r["strengths"]), improvements=json.loads(r["improvements"]),
            examiner_tip=r["examiner_tip"], topic=r["topic"], timestamp=r["timestamp"],
        )


# ── Topic Progress ───────────────────────────────────────────────────


class TopicProgressStoreDB:
    """DB-backed TopicProgressStore."""

    def __init__(self, user_id: int = 1):
        self.user_id = user_id

    def get(self, subject: str) -> TopicProgress:
        db = get_db()
        rows = db.execute(
            "SELECT topic_id, subtopic, attempts, avg_percentage, last_practiced "
            "FROM topic_progress WHERE user_id = ? AND subject = ?",
            (self.user_id, subject),
        ).fetchall()
        tp = TopicProgress(subject=subject)
        for r in rows:
            tid = r["topic_id"]
            if tid not in tp.topics:
                tp.topics[tid] = []
            tp.topics[tid].append(TopicAttempt(
                subtopic=r["subtopic"], attempts=r["attempts"],
                avg_percentage=r["avg_percentage"], last_practiced=r["last_practiced"],
            ))
        return tp

    def record(self, subject: str, topic_id: str, subtopic: str, percentage: float) -> None:
        db = get_db()
        row = db.execute(
            "SELECT attempts, avg_percentage FROM topic_progress "
            "WHERE user_id=? AND subject=? AND topic_id=? AND subtopic=?",
            (self.user_id, subject, topic_id, subtopic),
        ).fetchone()
        now = datetime.now().isoformat()
        if row:
            old_total = row["avg_percentage"] * row["attempts"]
            new_attempts = row["attempts"] + 1
            new_avg = round((old_total + percentage) / new_attempts, 1)
            db.execute(
                "UPDATE topic_progress SET attempts=?, avg_percentage=?, last_practiced=? "
                "WHERE user_id=? AND subject=? AND topic_id=? AND subtopic=?",
                (new_attempts, new_avg, now, self.user_id, subject, topic_id, subtopic),
            )
        else:
            db.execute(
                "INSERT INTO topic_progress (user_id, subject, topic_id, subtopic, attempts, avg_percentage, last_practiced) "
                "VALUES (?, ?, ?, ?, 1, ?, ?)",
                (self.user_id, subject, topic_id, subtopic, percentage, now),
            )
        db.commit()


# ── Activity Log ─────────────────────────────────────────────────────


class ActivityLogDB:
    """DB-backed ActivityLog."""

    def __init__(self, user_id: int = 1):
        self.user_id = user_id

    @property
    def entries(self) -> list[ActivityEntry]:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM activity_log WHERE user_id = ? ORDER BY date, subject",
            (self.user_id,),
        ).fetchall()
        return [ActivityEntry(
            date=r["date"], subject=r["subject"],
            questions_attempted=r["questions_attempted"],
            questions_answered=r["questions_answered"],
            avg_grade=r["avg_grade"], avg_percentage=r["avg_percentage"],
            duration_minutes=r["duration_minutes"], timestamp=r["timestamp"],
        ) for r in rows]

    def record(self, subject: str, grade: float, percentage: float) -> None:
        db = get_db()
        today = date.today().isoformat()
        now = datetime.now().isoformat()
        row = db.execute(
            "SELECT id, avg_grade, avg_percentage, questions_answered FROM activity_log "
            "WHERE user_id=? AND date=? AND subject=?",
            (self.user_id, today, subject),
        ).fetchone()
        if row:
            old_total_grade = row["avg_grade"] * row["questions_answered"]
            old_total_pct = row["avg_percentage"] * row["questions_answered"]
            new_count = row["questions_answered"] + 1
            new_avg_grade = round((old_total_grade + grade) / new_count, 2)
            new_avg_pct = round((old_total_pct + percentage) / new_count, 1)
            db.execute(
                "UPDATE activity_log SET questions_attempted=questions_attempted+1, "
                "questions_answered=?, avg_grade=?, avg_percentage=?, timestamp=? WHERE id=?",
                (new_count, new_avg_grade, new_avg_pct, now, row["id"]),
            )
        else:
            db.execute(
                "INSERT INTO activity_log (user_id, date, subject, questions_attempted, "
                "questions_answered, avg_grade, avg_percentage, duration_minutes, timestamp) "
                "VALUES (?, ?, ?, 1, 1, ?, ?, 0, ?)",
                (self.user_id, today, subject, grade, percentage, now),
            )
        db.commit()

    def days_active_last_n(self, n: int = 30) -> int:
        db = get_db()
        cutoff = (date.today() - timedelta(days=n)).isoformat()
        row = db.execute(
            "SELECT COUNT(DISTINCT date) as cnt FROM activity_log WHERE user_id=? AND date >= ?",
            (self.user_id, cutoff),
        ).fetchone()
        return row["cnt"] if row else 0

    def streak(self) -> int:
        db = get_db()
        rows = db.execute(
            "SELECT DISTINCT date FROM activity_log WHERE user_id=? ORDER BY date DESC",
            (self.user_id,),
        ).fetchall()
        if not rows:
            return 0
        active_dates = [r["date"] for r in rows]
        today = date.today()
        latest = date.fromisoformat(active_dates[0])
        if (today - latest).days > 1:
            return 0
        count = 1
        for i in range(1, len(active_dates)):
            prev = date.fromisoformat(active_dates[i - 1])
            curr = date.fromisoformat(active_dates[i])
            if (prev - curr).days == 1:
                count += 1
            else:
                break
        return count

    def weekly_summary(self, n_weeks: int = 4) -> list[dict]:
        today = date.today()
        summaries = []
        for w in range(n_weeks):
            week_start = today - timedelta(days=today.weekday() + 7 * w)
            week_end = week_start + timedelta(days=6)
            db = get_db()
            rows = db.execute(
                "SELECT * FROM activity_log WHERE user_id=? AND date >= ? AND date <= ?",
                (self.user_id, week_start.isoformat(), week_end.isoformat()),
            ).fetchall()
            total_questions = sum(r["questions_answered"] for r in rows)
            subjects = list({r["subject"] for r in rows})
            grades = [r["avg_grade"] for r in rows]
            avg_grade = round(sum(grades) / len(grades), 1) if grades else 0
            summaries.append({
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
                "total_questions": total_questions,
                "subjects_studied": subjects,
                "avg_grade": avg_grade,
                "days_active": len({r["date"] for r in rows}),
            })
        return summaries

    def daily_heatmap(self, n_days: int = 90) -> list[dict]:
        today = date.today()
        cutoff = (today - timedelta(days=n_days - 1)).isoformat()
        db = get_db()
        rows = db.execute(
            "SELECT date, SUM(questions_answered) as cnt FROM activity_log "
            "WHERE user_id=? AND date >= ? GROUP BY date",
            (self.user_id, cutoff),
        ).fetchall()
        date_counts = {r["date"]: r["cnt"] for r in rows}
        return [
            {"date": (today - timedelta(days=n_days - 1 - i)).isoformat(),
             "count": date_counts.get((today - timedelta(days=n_days - 1 - i)).isoformat(), 0)}
            for i in range(n_days)
        ]

    def recent_activity(self, n: int = 10) -> list[dict]:
        db = get_db()
        rows = db.execute(
            "SELECT date, subject, questions_answered, avg_grade, avg_percentage "
            "FROM activity_log WHERE user_id=? ORDER BY timestamp DESC LIMIT ?",
            (self.user_id, n),
        ).fetchall()
        return [{"date": r["date"], "subject": r["subject"], "questions": r["questions_answered"],
                 "avg_grade": r["avg_grade"], "avg_percentage": r["avg_percentage"]} for r in rows]


# ── Review Schedule (SM-2) ───────────────────────────────────────────


class ReviewScheduleDB:
    """DB-backed ReviewSchedule with SM-2 algorithm."""

    def __init__(self, user_id: int = 1):
        self.user_id = user_id

    @property
    def items(self) -> list[ReviewItem]:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM review_schedule WHERE user_id=?", (self.user_id,)
        ).fetchall()
        return [ReviewItem(
            subject=r["subject"], topic=r["topic"], command_term=r["command_term"],
            last_reviewed=r["last_reviewed"], next_review=r["next_review"],
            interval_days=r["interval_days"], ease_factor=r["ease_factor"],
            review_count=r["review_count"],
        ) for r in rows]

    def record_review(self, subject: str, topic: str, command_term: str, grade: int) -> None:
        quality = self._grade_to_quality(grade)
        db = get_db()
        today = date.today().isoformat()
        row = db.execute(
            "SELECT id, review_count, interval_days, ease_factor FROM review_schedule "
            "WHERE user_id=? AND subject=? AND topic=? AND command_term=?",
            (self.user_id, subject, topic, command_term),
        ).fetchone()

        if row:
            review_count = row["review_count"] + 1
            interval = row["interval_days"]
            ef = row["ease_factor"]
        else:
            review_count = 1
            interval = 1
            ef = 2.5

        if quality < 3:
            interval = 1
        else:
            if review_count == 1:
                interval = 1
            elif review_count == 2:
                interval = 6
            else:
                interval = max(1, round(interval * ef))

        ef = max(1.3, ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
        next_review = (date.today() + timedelta(days=interval)).isoformat()

        if row:
            db.execute(
                "UPDATE review_schedule SET review_count=?, interval_days=?, ease_factor=?, "
                "last_reviewed=?, next_review=? WHERE id=?",
                (review_count, interval, ef, today, next_review, row["id"]),
            )
        else:
            db.execute(
                "INSERT INTO review_schedule (user_id, subject, topic, command_term, "
                "last_reviewed, next_review, interval_days, ease_factor, review_count) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (self.user_id, subject, topic, command_term, today, next_review, interval, ef, review_count),
            )
        db.commit()

    def due_today(self) -> list[ReviewItem]:
        db = get_db()
        today = date.today().isoformat()
        rows = db.execute(
            "SELECT * FROM review_schedule WHERE user_id=? AND next_review <= ?",
            (self.user_id, today),
        ).fetchall()
        return [ReviewItem(
            subject=r["subject"], topic=r["topic"], command_term=r["command_term"],
            last_reviewed=r["last_reviewed"], next_review=r["next_review"],
            interval_days=r["interval_days"], ease_factor=r["ease_factor"],
            review_count=r["review_count"],
        ) for r in rows]

    def due_this_week(self) -> list[ReviewItem]:
        db = get_db()
        week_end = (date.today() + timedelta(days=7)).isoformat()
        rows = db.execute(
            "SELECT * FROM review_schedule WHERE user_id=? AND next_review <= ?",
            (self.user_id, week_end),
        ).fetchall()
        return [ReviewItem(
            subject=r["subject"], topic=r["topic"], command_term=r["command_term"],
            last_reviewed=r["last_reviewed"], next_review=r["next_review"],
            interval_days=r["interval_days"], ease_factor=r["ease_factor"],
            review_count=r["review_count"],
        ) for r in rows]

    def _grade_to_quality(self, grade: int) -> int:
        mapping = {7: 5, 6: 4, 5: 3, 4: 2, 3: 1, 2: 0, 1: 0}
        return mapping.get(grade, 2)


# ── Gamification ─────────────────────────────────────────────────────


class GamificationProfileDB:
    """DB-backed GamificationProfile."""

    def __init__(self, user_id: int = 1):
        self.user_id = user_id

    def _row(self):
        db = get_db()
        return db.execute("SELECT * FROM gamification WHERE user_id=?", (self.user_id,)).fetchone()

    def _ensure(self):
        db = get_db()
        db.execute("INSERT OR IGNORE INTO gamification (user_id) VALUES (?)", (self.user_id,))
        db.commit()

    # --- Properties (read from DB each time for freshness) ---
    @property
    def total_xp(self) -> int:
        r = self._row()
        return r["total_xp"] if r else 0

    @property
    def daily_xp_today(self) -> int:
        r = self._row()
        if not r:
            return 0
        if r["daily_xp_date"] != date.today().isoformat():
            return 0
        return r["daily_xp_today"]

    @property
    def daily_goal_xp(self) -> int:
        r = self._row()
        return r["daily_goal_xp"] if r else 100

    @property
    def current_streak(self) -> int:
        r = self._row()
        return r["current_streak"] if r else 0

    @property
    def longest_streak(self) -> int:
        r = self._row()
        return r["longest_streak"] if r else 0

    @property
    def badges(self) -> list[str]:
        r = self._row()
        return json.loads(r["badges"]) if r else []

    @property
    def streak_freeze_available(self) -> int:
        r = self._row()
        return r["streak_freeze_available"] if r else 0

    @property
    def total_questions_answered(self) -> int:
        r = self._row()
        return r["total_questions_answered"] if r else 0

    @total_questions_answered.setter
    def total_questions_answered(self, val: int):
        db = get_db()
        db.execute("UPDATE gamification SET total_questions_answered=? WHERE user_id=?", (val, self.user_id))
        db.commit()

    @property
    def total_flashcards_reviewed(self) -> int:
        r = self._row()
        return r["total_flashcards_reviewed"] if r else 0

    @total_flashcards_reviewed.setter
    def total_flashcards_reviewed(self, val: int):
        db = get_db()
        db.execute("UPDATE gamification SET total_flashcards_reviewed=? WHERE user_id=?", (val, self.user_id))
        db.commit()

    @property
    def subjects_practiced(self) -> list[str]:
        r = self._row()
        return json.loads(r["subjects_practiced"]) if r else []

    @subjects_practiced.setter
    def subjects_practiced(self, val: list[str]):
        db = get_db()
        db.execute("UPDATE gamification SET subjects_practiced=? WHERE user_id=?",
                    (json.dumps(val), self.user_id))
        db.commit()

    @property
    def level(self) -> int:
        return int(math.sqrt(self.total_xp / 50)) + 1

    @property
    def xp_for_current_level(self) -> int:
        return (self.level - 1) ** 2 * 50

    @property
    def xp_for_next_level(self) -> int:
        return self.level ** 2 * 50

    @property
    def xp_progress_pct(self) -> int:
        level_start = self.xp_for_current_level
        level_end = self.xp_for_next_level
        level_range = level_end - level_start
        if level_range <= 0:
            return 100
        return min(100, int((self.total_xp - level_start) / level_range * 100))

    @property
    def daily_goal_pct(self) -> int:
        dg = self.daily_goal_xp
        return min(100, int(self.daily_xp_today / dg * 100)) if dg > 0 else 0

    @property
    def streak_freeze_used_date(self) -> str:
        r = self._row()
        return r["streak_freeze_used_date"] if r else ""

    def award_xp(self, amount: int, reason: str = "") -> dict:
        self._ensure()
        db = get_db()
        today = date.today().isoformat()
        r = self._row()
        daily_xp = r["daily_xp_today"] if r["daily_xp_date"] == today else 0
        old_level = self.level

        new_total = r["total_xp"] + amount
        new_daily = daily_xp + amount

        db.execute(
            "UPDATE gamification SET total_xp=?, daily_xp_today=?, daily_xp_date=? WHERE user_id=?",
            (new_total, new_daily, today, self.user_id),
        )
        db.commit()

        new_level = int(math.sqrt(new_total / 50)) + 1
        result = {"xp_earned": amount, "total_xp": new_total, "new_badges": []}

        if new_level > old_level:
            result["level_up"] = new_level

        # Daily goal check
        dg = r["daily_goal_xp"]
        if new_daily >= dg and (new_daily - amount) < dg:
            db.execute(
                "UPDATE gamification SET total_xp = total_xp + ? WHERE user_id=?",
                (XP_AWARDS["daily_goal_complete"], self.user_id),
            )
            db.commit()
            result["daily_goal_complete"] = True

        return result

    def check_badges(self, grade: int = 0, subjects_count: int = 0,
                     syllabus_coverage: float = 0, mock_complete: bool = False, **kwargs) -> list[str]:
        r = self._row()
        if not r:
            return []
        current_badges = json.loads(r["badges"])
        new_badges = []
        checks = [
            ("first_question", r["total_questions_answered"] >= 1),
            ("streak_7", r["current_streak"] >= 7),
            ("streak_30", r["current_streak"] >= 30),
            ("grade_7_club", grade >= 7),
            ("century", r["total_questions_answered"] >= 100),
            ("all_subjects", subjects_count > 0 and len(json.loads(r["subjects_practiced"])) >= subjects_count),
            ("syllabus_50", syllabus_coverage >= 50),
            ("mock_complete", mock_complete),
            ("flashcard_50", r["total_flashcards_reviewed"] >= 50),
        ]
        for badge_id, condition in checks:
            if condition and badge_id not in current_badges:
                current_badges.append(badge_id)
                new_badges.append(badge_id)
        if new_badges:
            db = get_db()
            db.execute("UPDATE gamification SET badges=? WHERE user_id=?",
                        (json.dumps(current_badges), self.user_id))
            db.commit()
        return new_badges

    def update_streak(self, activity_log: ActivityLogDB) -> None:
        r = self._row()
        if not r:
            return
        db = get_db()
        rows = db.execute(
            "SELECT DISTINCT date FROM activity_log WHERE user_id=? ORDER BY date DESC",
            (self.user_id,),
        ).fetchall()
        if not rows:
            db.execute("UPDATE gamification SET current_streak=0 WHERE user_id=?", (self.user_id,))
            db.commit()
            return

        active_dates = [row["date"] for row in rows]
        today = date.today()
        latest = date.fromisoformat(active_dates[0])
        gap = (today - latest).days
        current_streak = r["current_streak"]
        longest = r["longest_streak"]
        freeze_avail = r["streak_freeze_available"]

        if gap <= 1:
            current_streak = activity_log.streak()
        elif gap == 2 and freeze_avail > 0:
            freeze_avail -= 1
            current_streak = activity_log.streak() + 1
            db.execute(
                "UPDATE gamification SET streak_freeze_available=?, streak_freeze_used_date=? WHERE user_id=?",
                (freeze_avail, (today - timedelta(days=1)).isoformat(), self.user_id),
            )
        else:
            current_streak = 0

        if current_streak > 0 and current_streak % 7 == 0:
            freeze_avail = min(freeze_avail + 1, 3)

        longest = max(longest, current_streak)
        db.execute(
            "UPDATE gamification SET current_streak=?, longest_streak=?, streak_freeze_available=? WHERE user_id=?",
            (current_streak, longest, freeze_avail, self.user_id),
        )
        db.commit()

    def save(self) -> None:
        pass  # All mutations are committed immediately


# ── Flashcard Deck ───────────────────────────────────────────────────


class FlashcardDeckDB:
    """DB-backed FlashcardDeck with SM-2 spaced repetition."""

    def __init__(self, user_id: int = 1):
        self.user_id = user_id

    @property
    def cards(self) -> list[Flashcard]:
        db = get_db()
        rows = db.execute("SELECT * FROM flashcards WHERE user_id=? ORDER BY created_at", (self.user_id,)).fetchall()
        return [Flashcard(**{k: r[k] for k in r.keys() if k != "user_id"}) for r in rows]

    def add(self, card: Flashcard) -> None:
        if not card.id:
            card.id = f"fc_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}"
        if not card.next_review:
            card.next_review = date.today().isoformat()
        if not card.created_at:
            card.created_at = datetime.now().isoformat()
        db = get_db()
        db.execute(
            "INSERT INTO flashcards (id, user_id, front, back, subject, topic, source, "
            "interval_days, ease_factor, next_review, last_reviewed, review_count, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (card.id, self.user_id, card.front, card.back, card.subject, card.topic,
             card.source, card.interval_days, card.ease_factor, card.next_review,
             card.last_reviewed, card.review_count, card.created_at),
        )
        db.commit()

    def delete(self, card_id: str) -> bool:
        db = get_db()
        cur = db.execute("DELETE FROM flashcards WHERE id=? AND user_id=?", (card_id, self.user_id))
        db.commit()
        return cur.rowcount > 0

    def due_today(self) -> list[Flashcard]:
        db = get_db()
        today = date.today().isoformat()
        rows = db.execute(
            "SELECT * FROM flashcards WHERE user_id=? AND next_review <= ?",
            (self.user_id, today),
        ).fetchall()
        return [Flashcard(**{k: r[k] for k in r.keys() if k != "user_id"}) for r in rows]

    def due_count(self) -> int:
        db = get_db()
        today = date.today().isoformat()
        row = db.execute(
            "SELECT COUNT(*) as cnt FROM flashcards WHERE user_id=? AND next_review <= ?",
            (self.user_id, today),
        ).fetchone()
        return row["cnt"] if row else 0

    def by_subject(self, subject: str) -> list[Flashcard]:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM flashcards WHERE user_id=? AND subject=?",
            (self.user_id, subject),
        ).fetchall()
        return [Flashcard(**{k: r[k] for k in r.keys() if k != "user_id"}) for r in rows]

    def review(self, card_id: str, rating: int) -> None:
        db = get_db()
        row = db.execute(
            "SELECT * FROM flashcards WHERE id=? AND user_id=?", (card_id, self.user_id)
        ).fetchone()
        if not row:
            return
        review_count = row["review_count"] + 1
        today = date.today().isoformat()
        quality_map = {1: 0, 2: 2, 3: 3, 4: 5}
        quality = quality_map.get(rating, 3)
        interval = row["interval_days"]
        ef = row["ease_factor"]

        if quality < 3:
            interval = 1
        else:
            if review_count == 1:
                interval = 1
            elif review_count == 2:
                interval = 6
            else:
                interval = max(1, round(interval * ef))
        ef = max(1.3, ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
        next_review = (date.today() + timedelta(days=interval)).isoformat()

        db.execute(
            "UPDATE flashcards SET review_count=?, last_reviewed=?, interval_days=?, "
            "ease_factor=?, next_review=? WHERE id=?",
            (review_count, today, interval, ef, next_review, card_id),
        )
        db.commit()

    def auto_create_from_grade(self, question: str, model_answer: str,
                                subject: str, topic: str, percentage: int) -> Optional[Flashcard]:
        if percentage >= 60:
            return None
        db = get_db()
        existing = db.execute(
            "SELECT 1 FROM flashcards WHERE user_id=? AND front=? AND subject=?",
            (self.user_id, question, subject),
        ).fetchone()
        if existing:
            return None
        card = Flashcard(
            id=f"fc_auto_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}",
            front=question,
            back=model_answer or "Review this topic",
            subject=subject,
            topic=topic,
            source="auto_grading",
        )
        self.add(card)
        return card


# ── Misconception Log ────────────────────────────────────────────────


class MisconceptionLogDB:
    """DB-backed MisconceptionLog."""

    def __init__(self, user_id: int = 1):
        self.user_id = user_id

    def scan_improvements(self, improvements: list[str], subject: str) -> list[str]:
        if not improvements:
            return []
        feedback_text = " ".join(improvements).lower()
        detected = []
        for pattern_id, pattern_def in MISCONCEPTION_PATTERNS.items():
            for keyword in pattern_def["keywords"]:
                if keyword in feedback_text:
                    detected.append(pattern_id)
                    self._record(pattern_id, subject)
                    break
        return detected

    def active_misconceptions(self, subject: str = "") -> list[dict]:
        db = get_db()
        if subject:
            rows = db.execute(
                "SELECT * FROM misconceptions WHERE user_id=? AND subject=? ORDER BY count DESC",
                (self.user_id, subject),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM misconceptions WHERE user_id=? ORDER BY count DESC",
                (self.user_id,),
            ).fetchall()
        result = []
        for r in rows:
            pattern_def = MISCONCEPTION_PATTERNS.get(r["pattern_id"], {})
            result.append({
                "pattern_id": r["pattern_id"],
                "name": pattern_def.get("name", r["pattern_id"]),
                "description": pattern_def.get("description", ""),
                "subject": r["subject"],
                "count": r["count"],
                "trending": r["trending"],
                "first_seen": r["first_seen"],
                "last_seen": r["last_seen"],
            })
        return result

    def _record(self, pattern_id: str, subject: str) -> None:
        db = get_db()
        now = datetime.now().isoformat()
        row = db.execute(
            "SELECT id, count FROM misconceptions WHERE user_id=? AND pattern_id=? AND subject=?",
            (self.user_id, pattern_id, subject),
        ).fetchone()
        if row:
            new_count = row["count"] + 1
            trending = "persisting" if new_count > row["count"] + 2 else "new"
            db.execute(
                "UPDATE misconceptions SET count=?, last_seen=?, trending=? WHERE id=?",
                (new_count, now, trending, row["id"]),
            )
        else:
            db.execute(
                "INSERT INTO misconceptions (user_id, pattern_id, subject, count, first_seen, last_seen, trending) "
                "VALUES (?, ?, ?, 1, ?, ?, 'new')",
                (self.user_id, pattern_id, subject, now, now),
            )
        db.commit()


# ── Mock Exam Reports ────────────────────────────────────────────────


class MockExamReportStoreDB:
    """DB-backed MockExamReportStore."""

    def __init__(self, user_id: int = 1):
        self.user_id = user_id

    @property
    def reports(self) -> list[MockExamReport]:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM mock_reports WHERE user_id=? ORDER BY created_at",
            (self.user_id,),
        ).fetchall()
        return [self._row_to_report(r) for r in rows]

    def add(self, report: MockExamReport) -> None:
        db = get_db()
        db.execute(
            "INSERT INTO mock_reports (id, user_id, subject, level, date, total_marks_earned, "
            "total_marks_possible, percentage, grade, questions, command_term_breakdown, "
            "time_taken_minutes, improvements, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (report.id, self.user_id, report.subject, report.level, report.date,
             report.total_marks_earned, report.total_marks_possible, report.percentage,
             report.grade, json.dumps(report.questions),
             json.dumps(report.command_term_breakdown), report.time_taken_minutes,
             json.dumps(report.improvements), report.created_at),
        )
        db.commit()

    def by_subject(self, subject: str) -> list[MockExamReport]:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM mock_reports WHERE user_id=? AND subject=? ORDER BY created_at",
            (self.user_id, subject),
        ).fetchall()
        return [self._row_to_report(r) for r in rows]

    def recent(self, n: int = 5) -> list[MockExamReport]:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM mock_reports WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (self.user_id, n),
        ).fetchall()
        return [self._row_to_report(r) for r in rows]

    def save(self) -> None:
        pass  # Mutations are committed immediately

    def _row_to_report(self, r) -> MockExamReport:
        return MockExamReport(
            id=r["id"], subject=r["subject"], level=r["level"], date=r["date"],
            total_marks_earned=r["total_marks_earned"], total_marks_possible=r["total_marks_possible"],
            percentage=r["percentage"], grade=r["grade"],
            questions=json.loads(r["questions"]),
            command_term_breakdown=json.loads(r["command_term_breakdown"]),
            time_taken_minutes=r["time_taken_minutes"],
            improvements=json.loads(r["improvements"]), created_at=r["created_at"],
        )


# ── Notification Store ───────────────────────────────────────────────


class NotificationStoreDB:
    """DB-backed NotificationStore."""

    def __init__(self, user_id: int = 1):
        self.user_id = user_id

    def add(self, notif: Notification) -> None:
        db = get_db()
        db.execute(
            "INSERT OR IGNORE INTO notifications (id, user_id, type, title, body, "
            "created_at, read, dismissed, action_url, data) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (notif.id, self.user_id, notif.type, notif.title, notif.body,
             notif.created_at, 1 if notif.read else 0, 1 if notif.dismissed else 0,
             notif.action_url, json.dumps(notif.data)),
        )
        db.commit()

    def unread_count(self) -> int:
        db = get_db()
        row = db.execute(
            "SELECT COUNT(*) as cnt FROM notifications WHERE user_id=? AND read=0 AND dismissed=0",
            (self.user_id,),
        ).fetchone()
        return row["cnt"] if row else 0

    def recent(self, n: int = 20) -> list[Notification]:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM notifications WHERE user_id=? AND dismissed=0 ORDER BY created_at DESC LIMIT ?",
            (self.user_id, n),
        ).fetchall()
        return [self._row_to_notif(r) for r in rows]

    def has_today(self, notif_type: str) -> bool:
        db = get_db()
        today = date.today().isoformat()
        row = db.execute(
            "SELECT 1 FROM notifications WHERE user_id=? AND type=? AND created_at LIKE ?",
            (self.user_id, notif_type, f"{today}%"),
        ).fetchone()
        return row is not None

    def mark_read(self, notif_id: str) -> None:
        db = get_db()
        db.execute("UPDATE notifications SET read=1 WHERE id=? AND user_id=?", (notif_id, self.user_id))
        db.commit()

    def mark_all_read(self) -> None:
        db = get_db()
        db.execute("UPDATE notifications SET read=1 WHERE user_id=?", (self.user_id,))
        db.commit()

    def dismiss(self, notif_id: str) -> None:
        db = get_db()
        db.execute("UPDATE notifications SET dismissed=1 WHERE id=? AND user_id=?", (notif_id, self.user_id))
        db.commit()

    def _row_to_notif(self, r) -> Notification:
        return Notification(
            id=r["id"], type=r["type"], title=r["title"], body=r["body"],
            created_at=r["created_at"], read=bool(r["read"]),
            dismissed=bool(r["dismissed"]), action_url=r["action_url"],
            data=json.loads(r["data"]),
        )


# ── Shared Questions ─────────────────────────────────────────────────


class SharedQuestionStoreDB:
    """DB-backed SharedQuestionStore."""

    def __init__(self, user_id: int = 1):
        self.user_id = user_id

    @property
    def sets(self) -> list[SharedQuestionSet]:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM shared_questions WHERE user_id=? ORDER BY created_at",
            (self.user_id,),
        ).fetchall()
        return [SharedQuestionSet(
            id=r["id"], title=r["title"], description=r["description"],
            author=r["author"], subject=r["subject"], topic=r["topic"],
            level=r["level"], questions=json.loads(r["questions"]),
            created_at=r["created_at"], import_count=r["import_count"],
        ) for r in rows]

    def export_set(self, title: str, description: str, subject: str,
                   topic: str, level: str, questions: list[dict], author: str) -> SharedQuestionSet:
        qset = SharedQuestionSet(
            id=f"qs_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            title=title, description=description, author=author,
            subject=subject, topic=topic, level=level, questions=questions,
        )
        db = get_db()
        db.execute(
            "INSERT INTO shared_questions (id, user_id, title, description, author, "
            "subject, topic, level, questions, created_at, import_count) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)",
            (qset.id, self.user_id, title, description, author,
             subject, topic, level, json.dumps(questions), qset.created_at),
        )
        db.commit()
        return qset

    def import_set(self, data: dict) -> SharedQuestionSet:
        qset = SharedQuestionSet(**data)
        qset.import_count += 1
        db = get_db()
        db.execute(
            "INSERT INTO shared_questions (id, user_id, title, description, author, "
            "subject, topic, level, questions, created_at, import_count) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (qset.id, self.user_id, qset.title, qset.description, qset.author,
             qset.subject, qset.topic, qset.level, json.dumps(qset.questions),
             qset.created_at, qset.import_count),
        )
        db.commit()
        return qset

    def to_json(self, set_id: str) -> str:
        db = get_db()
        row = db.execute("SELECT * FROM shared_questions WHERE id=?", (set_id,)).fetchone()
        if not row:
            return ""
        return json.dumps({
            "id": row["id"], "title": row["title"], "description": row["description"],
            "author": row["author"], "subject": row["subject"], "topic": row["topic"],
            "level": row["level"], "questions": json.loads(row["questions"]),
            "created_at": row["created_at"], "import_count": row["import_count"],
        }, indent=2)


# ── Study Plan ───────────────────────────────────────────────────────


class StudyPlanDB:
    """DB-backed StudyPlan."""

    def __init__(self, user_id: int = 1):
        self.user_id = user_id

    def save(self, generated_date: str, exam_date: str, daily_plans: list[DailyPlan]) -> None:
        db = get_db()
        # Delete old plans for this user
        db.execute("DELETE FROM study_plans WHERE user_id=?", (self.user_id,))
        plans_data = [
            {
                "date": dp.date,
                "estimated_minutes": dp.estimated_minutes,
                "tasks": [asdict(t) for t in dp.tasks],
            }
            for dp in daily_plans
        ]
        db.execute(
            "INSERT INTO study_plans (user_id, generated_date, exam_date, daily_plans) VALUES (?, ?, ?, ?)",
            (self.user_id, generated_date, exam_date, json.dumps(plans_data)),
        )
        db.commit()

    def load(self) -> Optional[dict]:
        """Return {generated_date, exam_date, daily_plans} or None."""
        db = get_db()
        row = db.execute(
            "SELECT * FROM study_plans WHERE user_id=? ORDER BY id DESC LIMIT 1",
            (self.user_id,),
        ).fetchone()
        if not row:
            return None
        plans_data = json.loads(row["daily_plans"])
        daily_plans = []
        for dp_data in plans_data:
            tasks = [StudyTask(**t) for t in dp_data.get("tasks", [])]
            daily_plans.append(DailyPlan(
                date=dp_data["date"],
                estimated_minutes=dp_data.get("estimated_minutes", 0),
                tasks=tasks,
            ))
        return {
            "generated_date": row["generated_date"],
            "exam_date": row["exam_date"],
            "daily_plans": daily_plans,
        }

    def update_task(self, day_date: str, task_index: int) -> Optional[bool]:
        """Toggle a task's completed status. Returns new status or None if not found."""
        plan_data = self.load()
        if not plan_data:
            return None
        for dp in plan_data["daily_plans"]:
            if dp.date == day_date and 0 <= task_index < len(dp.tasks):
                dp.tasks[task_index].completed = not dp.tasks[task_index].completed
                self.save(plan_data["generated_date"], plan_data["exam_date"], plan_data["daily_plans"])
                return dp.tasks[task_index].completed
        return None


# ── Writing Profile ──────────────────────────────────────────────────


class WritingProfileDB:
    """DB-backed WritingProfile."""

    def __init__(self, user_id: int = 1):
        self.user_id = user_id

    def save(self, *, verbosity="", terminology_usage="", argument_structure="",
             common_patterns=None, summary="", analyzed_count=0, last_updated="") -> None:
        db = get_db()
        db.execute(
            "INSERT OR REPLACE INTO writing_profiles "
            "(user_id, verbosity, terminology_usage, argument_structure, "
            "common_patterns, summary, analyzed_count, last_updated) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (self.user_id, verbosity, terminology_usage, argument_structure,
             json.dumps(common_patterns or []), summary, analyzed_count, last_updated),
        )
        db.commit()

    def load(self) -> Optional[dict]:
        db = get_db()
        row = db.execute("SELECT * FROM writing_profiles WHERE user_id=?", (self.user_id,)).fetchone()
        if not row:
            return None
        return {
            "verbosity": row["verbosity"],
            "terminology_usage": row["terminology_usage"],
            "argument_structure": row["argument_structure"],
            "common_patterns": json.loads(row["common_patterns"]),
            "summary": row["summary"],
            "analyzed_count": row["analyzed_count"],
            "last_updated": row["last_updated"],
        }

    def exists(self) -> bool:
        db = get_db()
        return db.execute("SELECT 1 FROM writing_profiles WHERE user_id=?", (self.user_id,)).fetchone() is not None

    def grader_context(self) -> str:
        data = self.load()
        if not data or not data["summary"]:
            return ""
        return (
            f"\n\nSTUDENT WRITING PROFILE (personalize feedback based on this):\n"
            f"{data['summary']}\n"
            f"Verbosity: {data['verbosity']}\n"
            f"Terminology usage: {data['terminology_usage']}\n"
            f"Argument structure: {data['argument_structure']}\n"
        )


# ── Parent Config ────────────────────────────────────────────────────


class ParentConfigDB:
    """DB-backed ParentConfig."""

    def __init__(self, user_id: int = 1):
        self.user_id = user_id
        self._ensure()

    def _ensure(self):
        db = get_db()
        db.execute("INSERT OR IGNORE INTO parent_config (user_id) VALUES (?)", (self.user_id,))
        db.commit()

    def _row(self):
        db = get_db()
        return db.execute("SELECT * FROM parent_config WHERE user_id=?", (self.user_id,)).fetchone()

    # Properties
    @property
    def enabled(self) -> bool:
        return bool(self._row()["enabled"])

    @property
    def token(self) -> str:
        return self._row()["token"]

    @property
    def created_at(self) -> str:
        return self._row()["created_at"]

    @property
    def student_display_name(self) -> str:
        return self._row()["student_display_name"]

    @property
    def show_subject_grades(self) -> bool:
        return bool(self._row()["show_subject_grades"])

    @property
    def show_recent_activity(self) -> bool:
        return bool(self._row()["show_recent_activity"])

    @property
    def show_study_consistency(self) -> bool:
        return bool(self._row()["show_study_consistency"])

    @property
    def show_command_term_stats(self) -> bool:
        return bool(self._row()["show_command_term_stats"])

    @property
    def show_insights(self) -> bool:
        return bool(self._row()["show_insights"])

    @property
    def show_exam_countdown(self) -> bool:
        return bool(self._row()["show_exam_countdown"])

    def generate_token(self) -> str:
        token = secrets.token_hex(16)
        expires = (datetime.now() + timedelta(days=90)).isoformat()
        db = get_db()
        db.execute(
            "UPDATE parent_config SET token=?, created_at=?, token_expires_at=? WHERE user_id=?",
            (token, datetime.now().isoformat(), expires, self.user_id),
        )
        db.commit()
        return token

    def save(self, **kwargs) -> None:
        db = get_db()
        fields = ["enabled", "token", "student_display_name",
                   "show_subject_grades", "show_recent_activity", "show_study_consistency",
                   "show_command_term_stats", "show_insights", "show_exam_countdown"]
        sets = []
        vals = []
        for f in fields:
            if f in kwargs:
                sets.append(f"{f}=?")
                v = kwargs[f]
                vals.append(1 if v is True else (0 if v is False else v))
        if sets:
            vals.append(self.user_id)
            db.execute(f"UPDATE parent_config SET {', '.join(sets)} WHERE user_id=?", vals)
            db.commit()

    def save_all(self, *, enabled=None, token=None, student_display_name=None,
                 show_subject_grades=None, show_recent_activity=None,
                 show_study_consistency=None, show_command_term_stats=None,
                 show_insights=None, show_exam_countdown=None) -> None:
        """Update all provided fields."""
        kwargs = {}
        for name, val in [("enabled", enabled), ("token", token),
                          ("student_display_name", student_display_name),
                          ("show_subject_grades", show_subject_grades),
                          ("show_recent_activity", show_recent_activity),
                          ("show_study_consistency", show_study_consistency),
                          ("show_command_term_stats", show_command_term_stats),
                          ("show_insights", show_insights),
                          ("show_exam_countdown", show_exam_countdown)]:
            if val is not None:
                kwargs[name] = val
        if kwargs:
            self.save(**kwargs)

    @staticmethod
    def load_by_token(token: str) -> Optional[ParentConfigDB]:
        db = get_db()
        row = db.execute(
            "SELECT user_id, token_expires_at FROM parent_config WHERE token=? AND enabled=1",
            (token,),
        ).fetchone()
        if not row:
            return None
        # Check expiration
        expires_at = row["token_expires_at"] if "token_expires_at" in row.keys() else ""
        if expires_at:
            try:
                if datetime.now() > datetime.fromisoformat(expires_at):
                    return None
            except (ValueError, TypeError):
                pass
        return ParentConfigDB(row["user_id"])


# ── Upload Store ─────────────────────────────────────────────────────


class UploadStoreDB:
    """DB-backed upload metadata store."""

    def __init__(self, user_id: int = 1):
        self.user_id = user_id

    def load(self) -> list[dict]:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM uploads WHERE user_id=? ORDER BY uploaded_at",
            (self.user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def add(self, entry: dict) -> None:
        db = get_db()
        db.execute(
            "INSERT INTO uploads (id, user_id, filename, doc_type, subject, level, chunks, uploaded_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (entry["id"], self.user_id, entry["filename"], entry.get("doc_type", ""),
             entry.get("subject", ""), entry.get("level", ""),
             entry.get("chunks", 0), entry.get("uploaded_at", "")),
        )
        db.commit()

    def delete(self, doc_id: str) -> Optional[dict]:
        db = get_db()
        row = db.execute("SELECT * FROM uploads WHERE id=? AND user_id=?", (doc_id, self.user_id)).fetchone()
        if not row:
            return None
        db.execute("DELETE FROM uploads WHERE id=?", (doc_id,))
        db.commit()
        return dict(row)


# ── IB Lifecycle ─────────────────────────────────────────────────────


class IBLifecycleDB:
    """DB-backed IBLifecycle managing EE, IA, TOK, CAS."""

    def __init__(self, user_id: int = 1):
        self.user_id = user_id

    # --- Extended Essay ---

    @property
    def extended_essay(self) -> ExtendedEssay:
        db = get_db()
        row = db.execute("SELECT * FROM extended_essays WHERE user_id=?", (self.user_id,)).fetchone()
        if not row:
            return ExtendedEssay()
        ee = ExtendedEssay(
            subject=row["subject"], research_question=row["research_question"],
            supervisor=row["supervisor"], word_count=row["word_count"],
            milestones=self._load_milestones("ee", ""),
        )
        return ee

    # --- Internal Assessments ---

    @property
    def internal_assessments(self) -> list[InternalAssessment]:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM internal_assessments WHERE user_id=? ORDER BY id",
            (self.user_id,),
        ).fetchall()
        result = []
        for r in rows:
            ia = InternalAssessment(
                subject=r["subject"], title=r["title"], word_count=r["word_count"],
                milestones=self._load_milestones("ia", r["subject"]),
            )
            result.append(ia)
        return result

    # --- TOK ---

    @property
    def tok(self) -> TOKProgress:
        db = get_db()
        row = db.execute("SELECT * FROM tok_progress WHERE user_id=?", (self.user_id,)).fetchone()
        if not row:
            return TOKProgress()
        return TOKProgress(
            essay_title=row["essay_title"],
            prescribed_title_number=row["prescribed_title_number"],
            exhibition_theme=row["exhibition_theme"],
            milestones=self._load_milestones("tok", ""),
        )

    # --- CAS ---

    @property
    def cas_reflections(self) -> list[CASReflection]:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM cas_reflections WHERE user_id=? ORDER BY date",
            (self.user_id,),
        ).fetchall()
        return [CASReflection(
            id=r["id"], strand=r["strand"], title=r["title"],
            description=r["description"], date=r["date"],
            learning_outcome=r["learning_outcome"], hours=r["hours"],
        ) for r in rows]

    @property
    def cas_hours(self) -> dict[str, float]:
        db = get_db()
        rows = db.execute(
            "SELECT strand, SUM(hours) as total FROM cas_reflections WHERE user_id=? GROUP BY strand",
            (self.user_id,),
        ).fetchall()
        hours = {"Creativity": 0.0, "Activity": 0.0, "Service": 0.0}
        for r in rows:
            if r["strand"] in hours:
                hours[r["strand"]] = r["total"] or 0.0
        return hours

    # --- Milestone operations ---

    def _load_milestones(self, parent_type: str, parent_subject: str) -> list[Milestone]:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM milestones WHERE user_id=? AND parent_type=? AND parent_subject=? ORDER BY sort_order",
            (self.user_id, parent_type, parent_subject),
        ).fetchall()
        return [Milestone(
            id=r["id"], title=r["title"], due_date=r["due_date"],
            completed=bool(r["completed"]), completed_date=r["completed_date"],
            notes=r["notes"],
        ) for r in rows]

    def total_milestones(self) -> int:
        db = get_db()
        row = db.execute("SELECT COUNT(*) as cnt FROM milestones WHERE user_id=?", (self.user_id,)).fetchone()
        return row["cnt"] if row else 0

    def completed_milestones(self) -> int:
        db = get_db()
        row = db.execute(
            "SELECT COUNT(*) as cnt FROM milestones WHERE user_id=? AND completed=1",
            (self.user_id,),
        ).fetchone()
        return row["cnt"] if row else 0

    def next_milestone(self, section: str = "all") -> Optional[Milestone]:
        db = get_db()
        if section == "all":
            row = db.execute(
                "SELECT * FROM milestones WHERE user_id=? AND completed=0 ORDER BY sort_order LIMIT 1",
                (self.user_id,),
            ).fetchone()
        else:
            row = db.execute(
                "SELECT * FROM milestones WHERE user_id=? AND parent_type=? AND completed=0 ORDER BY sort_order LIMIT 1",
                (self.user_id, section),
            ).fetchone()
        if not row:
            return None
        return Milestone(id=row["id"], title=row["title"], due_date=row["due_date"],
                        completed=bool(row["completed"]), completed_date=row["completed_date"],
                        notes=row["notes"])

    def toggle_milestone(self, milestone_id: str) -> bool:
        db = get_db()
        row = db.execute(
            "SELECT completed FROM milestones WHERE user_id=? AND id=?",
            (self.user_id, milestone_id),
        ).fetchone()
        if not row:
            return False
        new_state = not bool(row["completed"])
        completed_date = datetime.now().isoformat() if new_state else ""
        db.execute(
            "UPDATE milestones SET completed=?, completed_date=? WHERE user_id=? AND id=?",
            (1 if new_state else 0, completed_date, self.user_id, milestone_id),
        )
        db.commit()
        return new_state

    def add_cas_reflection(self, reflection: CASReflection) -> None:
        if not reflection.id:
            reflection.id = f"cas_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}"
        db = get_db()
        db.execute(
            "INSERT INTO cas_reflections (id, user_id, strand, title, description, date, learning_outcome, hours) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (reflection.id, self.user_id, reflection.strand, reflection.title,
             reflection.description, reflection.date, reflection.learning_outcome, reflection.hours),
        )
        db.commit()

    def get_ia_for_subject(self, subject: str) -> Optional[InternalAssessment]:
        for ia in self.internal_assessments:
            if ia.subject == subject:
                return ia
        return None

    def update_ee(self, **kwargs) -> None:
        db = get_db()
        db.execute(
            "INSERT OR REPLACE INTO extended_essays (user_id, subject, research_question, supervisor, word_count) "
            "VALUES (?, ?, ?, ?, ?)",
            (self.user_id,
             kwargs.get("subject", self.extended_essay.subject),
             kwargs.get("research_question", self.extended_essay.research_question),
             kwargs.get("supervisor", self.extended_essay.supervisor),
             kwargs.get("word_count", self.extended_essay.word_count)),
        )
        db.commit()

    def update_tok(self, **kwargs) -> None:
        db = get_db()
        db.execute(
            "INSERT OR REPLACE INTO tok_progress (user_id, essay_title, prescribed_title_number, exhibition_theme) "
            "VALUES (?, ?, ?, ?)",
            (self.user_id,
             kwargs.get("essay_title", self.tok.essay_title),
             kwargs.get("prescribed_title_number", self.tok.prescribed_title_number),
             kwargs.get("exhibition_theme", self.tok.exhibition_theme)),
        )
        db.commit()

    def update_ia(self, subject: str, **kwargs) -> None:
        db = get_db()
        db.execute(
            "UPDATE internal_assessments SET title=?, word_count=? WHERE user_id=? AND subject=?",
            (kwargs.get("title", ""), kwargs.get("word_count", 0), self.user_id, subject),
        )
        db.commit()

    def init_from_profile(self, subjects: list[str]) -> None:
        """Auto-populate IAs from student's subject list."""
        core_subjects = {"Theory of Knowledge", "Extended Essay"}
        db = get_db()
        existing = {r["subject"] for r in db.execute(
            "SELECT subject FROM internal_assessments WHERE user_id=?", (self.user_id,)
        ).fetchall()}

        # Ensure EE row exists
        db.execute("INSERT OR IGNORE INTO extended_essays (user_id) VALUES (?)", (self.user_id,))
        # Ensure TOK row exists
        db.execute("INSERT OR IGNORE INTO tok_progress (user_id) VALUES (?)", (self.user_id,))

        # Ensure EE milestones exist
        ee_defaults = ExtendedEssay().milestones
        for i, m in enumerate(ee_defaults):
            db.execute(
                "INSERT OR IGNORE INTO milestones (user_id, id, parent_type, parent_subject, title, sort_order) "
                "VALUES (?, ?, 'ee', '', ?, ?)",
                (self.user_id, m.id, m.title, i),
            )

        # Ensure TOK milestones exist
        tok_defaults = TOKProgress().milestones
        for i, m in enumerate(tok_defaults):
            db.execute(
                "INSERT OR IGNORE INTO milestones (user_id, id, parent_type, parent_subject, title, sort_order) "
                "VALUES (?, ?, 'tok', '', ?, ?)",
                (self.user_id, m.id, m.title, i),
            )

        for subject in subjects:
            if subject not in core_subjects and subject not in existing:
                db.execute(
                    "INSERT OR IGNORE INTO internal_assessments (user_id, subject) VALUES (?, ?)",
                    (self.user_id, subject),
                )
                subj_key = subject.lower().split(":")[0].strip().replace(" ", "_").replace("&", "")
                ia_milestones = [
                    (f"ia_{subj_key}_topic", "Topic chosen"),
                    (f"ia_{subj_key}_research", "Research complete"),
                    (f"ia_{subj_key}_draft", "First draft"),
                    (f"ia_{subj_key}_submit", "Submitted"),
                ]
                for i, (mid, title) in enumerate(ia_milestones):
                    db.execute(
                        "INSERT OR IGNORE INTO milestones (user_id, id, parent_type, parent_subject, title, sort_order) "
                        "VALUES (?, ?, 'ia', ?, ?, ?)",
                        (self.user_id, mid, subject, title, i),
                    )
        db.commit()

    def summary(self) -> dict:
        total = self.total_milestones()
        completed = self.completed_milestones()
        ee = self.extended_essay
        tok = self.tok

        def _section_progress(milestones):
            t = len(milestones)
            c = sum(1 for m in milestones if m.completed)
            next_m = next((m for m in milestones if not m.completed), None)
            return {
                "total": t, "completed": c,
                "pct": round(c / t * 100) if t > 0 else 0,
                "next": next_m.title if next_m else "All complete",
            }

        ias = self.internal_assessments
        return {
            "total_milestones": total,
            "completed_milestones": completed,
            "progress_pct": round(completed / total * 100) if total > 0 else 0,
            "ee_subject": ee.subject,
            "ee_rq": ee.research_question,
            "ee_progress": _section_progress(ee.milestones),
            "tok_title": tok.essay_title,
            "tok_progress": _section_progress(tok.milestones),
            "ia_count": len(ias),
            "ia_summaries": [
                {"subject": ia.subject, "title": ia.title,
                 "progress": _section_progress(ia.milestones)}
                for ia in ias
            ],
            "cas_hours": self.cas_hours,
            "cas_reflections_count": len(self.cas_reflections),
        }

    def save(self) -> None:
        pass  # All mutations committed immediately


# ── Grade History (from grader.py) ───────────────────────────────────


class GradeHistoryDB:
    """DB-backed grade history replacing grader.py's _save_history/_load_history."""

    def __init__(self, user_id: int = 1):
        self.user_id = user_id

    @property
    def history(self) -> list[dict]:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM grade_history WHERE user_id=? ORDER BY id",
            (self.user_id,),
        ).fetchall()
        return [{
            "question": r["question"], "answer": r["answer"],
            "mark_earned": r["mark_earned"], "mark_total": r["mark_total"],
            "grade": r["grade"], "percentage": r["percentage"],
            "strengths": json.loads(r["strengths"]),
            "improvements": json.loads(r["improvements"]),
            "examiner_tip": r["examiner_tip"],
            "full_commentary": r["full_commentary"],
            "model_answer": r["model_answer"],
            "raw_response": r["raw_response"],
            "timestamp": r["timestamp"],
        } for r in rows]

    def append(self, result) -> None:
        """Append a GradeResult to history."""
        db = get_db()
        db.execute(
            "INSERT INTO grade_history (user_id, question, answer, mark_earned, mark_total, "
            "grade, percentage, strengths, improvements, examiner_tip, full_commentary, "
            "model_answer, raw_response, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (self.user_id, result.question, result.answer, result.mark_earned,
             result.mark_total, result.grade, result.percentage,
             json.dumps(result.strengths), json.dumps(result.improvements),
             result.examiner_tip, result.full_commentary,
             getattr(result, "model_answer", ""), result.raw_response, result.timestamp),
        )
        db.commit()


# ── School Infrastructure ────────────────────────────────────────────


class SchoolStoreDB:
    """Manage schools."""

    @staticmethod
    def create(name: str, code: str) -> int:
        db = get_db()
        cur = db.execute(
            "INSERT INTO schools (name, code, created_at) VALUES (?, ?, ?)",
            (name, code, datetime.now().isoformat()),
        )
        db.commit()
        return cur.lastrowid

    @staticmethod
    def get_by_code(code: str) -> dict | None:
        db = get_db()
        row = db.execute("SELECT * FROM schools WHERE code = ?", (code,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def get(school_id: int) -> dict | None:
        db = get_db()
        row = db.execute("SELECT * FROM schools WHERE id = ?", (school_id,)).fetchone()
        return dict(row) if row else None


class ClassStoreDB:
    """Manage classes and membership."""

    @staticmethod
    def create(teacher_id: int, name: str, subject: str = "", level: str = "", school_id: int | None = None) -> dict:
        import secrets
        join_code = secrets.token_urlsafe(6)
        db = get_db()
        cur = db.execute(
            "INSERT INTO classes (school_id, teacher_id, name, subject, level, join_code, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (school_id, teacher_id, name, subject, level, join_code, datetime.now().isoformat()),
        )
        db.commit()
        return {"id": cur.lastrowid, "join_code": join_code}

    @staticmethod
    def get(class_id: int) -> dict | None:
        db = get_db()
        row = db.execute("SELECT * FROM classes WHERE id = ?", (class_id,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_by_join_code(code: str) -> dict | None:
        db = get_db()
        row = db.execute("SELECT * FROM classes WHERE join_code = ?", (code,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def teacher_classes(teacher_id: int) -> list[dict]:
        db = get_db()
        rows = db.execute(
            "SELECT c.*, COUNT(cm.user_id) as member_count "
            "FROM classes c LEFT JOIN class_members cm ON c.id = cm.class_id "
            "WHERE c.teacher_id = ? GROUP BY c.id ORDER BY c.created_at DESC",
            (teacher_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def join(class_id: int, user_id: int) -> bool:
        db = get_db()
        try:
            db.execute(
                "INSERT INTO class_members (class_id, user_id, joined_at) VALUES (?, ?, ?)",
                (class_id, user_id, datetime.now().isoformat()),
            )
            db.commit()
            return True
        except db.IntegrityError:
            return False

    @staticmethod
    def leave(class_id: int, user_id: int):
        db = get_db()
        db.execute("DELETE FROM class_members WHERE class_id = ? AND user_id = ?", (class_id, user_id))
        db.commit()

    @staticmethod
    def members(class_id: int) -> list[dict]:
        db = get_db()
        rows = db.execute(
            "SELECT u.id, u.name, u.email, cm.joined_at FROM class_members cm "
            "JOIN users u ON cm.user_id = u.id WHERE cm.class_id = ? ORDER BY u.name",
            (class_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def student_classes(user_id: int) -> list[dict]:
        db = get_db()
        rows = db.execute(
            "SELECT c.* FROM classes c JOIN class_members cm ON c.id = cm.class_id "
            "WHERE cm.user_id = ? ORDER BY c.name",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def class_avg_grades(class_id: int) -> dict:
        """Get average grades for class members by subject."""
        db = get_db()
        rows = db.execute(
            "SELECT g.subject_display, AVG(g.percentage) as avg_pct, COUNT(*) as cnt "
            "FROM grades g JOIN class_members cm ON g.user_id = cm.user_id "
            "WHERE cm.class_id = ? GROUP BY g.subject_display",
            (class_id,),
        ).fetchall()
        return {r["subject_display"]: {"avg_pct": round(r["avg_pct"], 1), "count": r["cnt"]} for r in rows}

    @staticmethod
    def student_progress(class_id: int) -> list[dict]:
        """Get per-student progress summary for a class."""
        db = get_db()
        rows = db.execute(
            "SELECT u.id, u.name, "
            "COUNT(g.id) as total_grades, "
            "COALESCE(AVG(g.percentage), 0) as avg_pct, "
            "MAX(g.timestamp) as last_active "
            "FROM class_members cm "
            "JOIN users u ON cm.user_id = u.id "
            "LEFT JOIN grades g ON g.user_id = u.id "
            "WHERE cm.class_id = ? GROUP BY u.id ORDER BY u.name",
            (class_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def topic_gaps(class_id: int) -> list[dict]:
        """Find topics where the class average is lowest — reveals syllabus gaps."""
        db = get_db()
        rows = db.execute(
            "SELECT g.topic, g.subject_display, "
            "AVG(g.percentage) as avg_pct, COUNT(*) as attempts, "
            "AVG(g.grade) as avg_grade "
            "FROM grades g JOIN class_members cm ON g.user_id = cm.user_id "
            "WHERE cm.class_id = ? AND g.topic != '' "
            "GROUP BY g.topic, g.subject_display "
            "HAVING attempts >= 2 "
            "ORDER BY avg_pct ASC LIMIT 20",
            (class_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def at_risk_students(class_id: int, pct_threshold: float = 45.0, inactive_days: int = 7) -> list[dict]:
        """Flag students who are at risk: low average OR inactive for N days."""
        db = get_db()
        cutoff = (datetime.now() - timedelta(days=inactive_days)).isoformat()
        rows = db.execute(
            "SELECT u.id, u.name, "
            "COUNT(g.id) as total_grades, "
            "COALESCE(AVG(g.percentage), 0) as avg_pct, "
            "MAX(g.timestamp) as last_active "
            "FROM class_members cm "
            "JOIN users u ON cm.user_id = u.id "
            "LEFT JOIN grades g ON g.user_id = u.id "
            "WHERE cm.class_id = ? "
            "GROUP BY u.id "
            "HAVING avg_pct < ? OR last_active < ? OR last_active IS NULL "
            "ORDER BY avg_pct ASC",
            (class_id, pct_threshold, cutoff),
        ).fetchall()
        result = []
        for r in rows:
            reasons = []
            if r["avg_pct"] < pct_threshold and r["total_grades"] > 0:
                reasons.append(f"Low average ({round(r['avg_pct'], 1)}%)")
            if r["last_active"] is None or r["last_active"] < cutoff:
                reasons.append(f"Inactive {inactive_days}+ days")
            if r["total_grades"] == 0:
                reasons.append("No activity")
            result.append({**dict(r), "risk_reasons": reasons})
        return result

    @staticmethod
    def export_class_csv(class_id: int) -> str:
        """Generate CSV string of class progress data for export."""
        import csv
        import io
        db = get_db()
        cls = db.execute("SELECT name, subject FROM classes WHERE id = ?", (class_id,)).fetchone()
        rows = db.execute(
            "SELECT u.name as student_name, g.subject_display, g.topic, "
            "g.command_term, g.grade, g.percentage, g.mark_earned, g.mark_total, "
            "g.timestamp "
            "FROM grades g "
            "JOIN class_members cm ON g.user_id = cm.user_id "
            "JOIN users u ON g.user_id = u.id "
            "WHERE cm.class_id = ? "
            "ORDER BY u.name, g.timestamp",
            (class_id,),
        ).fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Student", "Subject", "Topic", "Command Term",
                         "Grade", "Percentage", "Mark Earned", "Mark Total", "Date"])
        for r in rows:
            writer.writerow([r["student_name"], r["subject_display"], r["topic"],
                             r["command_term"], r["grade"], r["percentage"],
                             r["mark_earned"], r["mark_total"], r["timestamp"]])
        return output.getvalue()

    @staticmethod
    def grade_distribution(class_id: int) -> list[dict]:
        """Histogram data: grade 1-7 counts per subject for students in a class."""
        db = get_db()
        rows = db.execute(
            "SELECT g.subject_display, g.grade, COUNT(*) as cnt "
            "FROM grades g JOIN class_members cm ON g.user_id = cm.user_id "
            "WHERE cm.class_id = ? "
            "GROUP BY g.subject_display, g.grade "
            "ORDER BY g.subject_display, g.grade",
            (class_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def activity_heatmap(class_id: int) -> list[dict]:
        """Weekly study activity per student for the last 30 days."""
        db = get_db()
        cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        rows = db.execute(
            "SELECT u.name, al.date, SUM(al.duration_minutes) as minutes "
            "FROM activity_log al "
            "JOIN class_members cm ON al.user_id = cm.user_id "
            "JOIN users u ON al.user_id = u.id "
            "WHERE cm.class_id = ? AND al.date >= ? "
            "GROUP BY u.name, al.date "
            "ORDER BY u.name, al.date",
            (class_id, cutoff),
        ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def command_term_breakdown(class_id: int) -> list[dict]:
        """Class-wide command term performance stats."""
        db = get_db()
        rows = db.execute(
            "SELECT g.command_term, AVG(g.percentage) as avg_pct, COUNT(*) as cnt "
            "FROM grades g JOIN class_members cm ON g.user_id = cm.user_id "
            "WHERE cm.class_id = ? AND g.command_term != '' "
            "GROUP BY g.command_term "
            "ORDER BY avg_pct ASC",
            (class_id,),
        ).fetchall()
        return [dict(r) for r in rows]


class AssignmentStoreDB:
    """Manage assignments and submissions."""

    @staticmethod
    def create(class_id: int, title: str, description: str = "", due_date: str = "", config: dict | None = None) -> int:
        db = get_db()
        cur = db.execute(
            "INSERT INTO assignments (class_id, title, description, due_date, config, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (class_id, title, description, due_date, json.dumps(config or {}), datetime.now().isoformat()),
        )
        db.commit()
        return cur.lastrowid

    @staticmethod
    def list_for_class(class_id: int) -> list[dict]:
        db = get_db()
        rows = db.execute(
            "SELECT a.*, COUNT(s.id) as submission_count "
            "FROM assignments a LEFT JOIN assignment_submissions s ON a.id = s.assignment_id "
            "WHERE a.class_id = ? GROUP BY a.id ORDER BY a.due_date DESC",
            (class_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def get(assignment_id: int) -> dict | None:
        db = get_db()
        row = db.execute("SELECT * FROM assignments WHERE id = ?", (assignment_id,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def submit(assignment_id: int, user_id: int, score: float) -> bool:
        db = get_db()
        try:
            db.execute(
                "INSERT INTO assignment_submissions (assignment_id, user_id, submitted_at, score) "
                "VALUES (?, ?, ?, ?)",
                (assignment_id, user_id, datetime.now().isoformat(), score),
            )
            db.commit()
            return True
        except db.IntegrityError:
            return False

    @staticmethod
    def submissions(assignment_id: int) -> list[dict]:
        db = get_db()
        rows = db.execute(
            "SELECT s.*, u.name FROM assignment_submissions s "
            "JOIN users u ON s.user_id = u.id WHERE s.assignment_id = ? ORDER BY s.score DESC",
            (assignment_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def student_assignments(user_id: int) -> list[dict]:
        """Get assignments for classes the student belongs to."""
        db = get_db()
        rows = db.execute(
            "SELECT a.*, c.name as class_name, "
            "CASE WHEN s.id IS NOT NULL THEN 1 ELSE 0 END as submitted, "
            "s.score "
            "FROM assignments a "
            "JOIN class_members cm ON a.class_id = cm.class_id "
            "JOIN classes c ON a.class_id = c.id "
            "LEFT JOIN assignment_submissions s ON a.id = s.assignment_id AND s.user_id = ? "
            "WHERE cm.user_id = ? ORDER BY a.due_date ASC",
            (user_id, user_id),
        ).fetchall()
        return [dict(r) for r in rows]


# ── Study Groups & Social ────────────────────────────────────────────


class StudyGroupStoreDB:
    """Manage study groups."""

    @staticmethod
    def create(name: str, created_by: int, subject: str = "", level: str = "", max_members: int = 20) -> dict:
        import secrets
        invite_code = secrets.token_urlsafe(6)
        db = get_db()
        cur = db.execute(
            "INSERT INTO study_groups (name, subject, level, created_by, invite_code, max_members, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, subject, level, created_by, invite_code, max_members, datetime.now().isoformat()),
        )
        group_id = cur.lastrowid
        db.execute(
            "INSERT INTO group_members (group_id, user_id, role, joined_at) VALUES (?, ?, 'owner', ?)",
            (group_id, created_by, datetime.now().isoformat()),
        )
        db.commit()
        return {"id": group_id, "invite_code": invite_code}

    @staticmethod
    def get(group_id: int) -> dict | None:
        db = get_db()
        row = db.execute("SELECT * FROM study_groups WHERE id = ?", (group_id,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_by_invite(code: str) -> dict | None:
        db = get_db()
        row = db.execute("SELECT * FROM study_groups WHERE invite_code = ?", (code,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def join(group_id: int, user_id: int) -> bool:
        db = get_db()
        # Check max members
        group = db.execute("SELECT max_members FROM study_groups WHERE id = ?", (group_id,)).fetchone()
        if not group:
            return False
        count = db.execute("SELECT COUNT(*) as c FROM group_members WHERE group_id = ?", (group_id,)).fetchone()["c"]
        if count >= group["max_members"]:
            return False
        try:
            db.execute(
                "INSERT INTO group_members (group_id, user_id, role, joined_at) VALUES (?, ?, 'member', ?)",
                (group_id, user_id, datetime.now().isoformat()),
            )
            db.commit()
            return True
        except db.IntegrityError:
            return False

    @staticmethod
    def leave(group_id: int, user_id: int):
        db = get_db()
        db.execute("DELETE FROM group_members WHERE group_id = ? AND user_id = ?", (group_id, user_id))
        db.commit()

    @staticmethod
    def members(group_id: int) -> list[dict]:
        db = get_db()
        rows = db.execute(
            "SELECT u.id, u.name, gm.role, gm.joined_at, COALESCE(g.total_xp, 0) as xp "
            "FROM group_members gm JOIN users u ON gm.user_id = u.id "
            "LEFT JOIN gamification g ON g.user_id = u.id "
            "WHERE gm.group_id = ? ORDER BY gm.role DESC, u.name",
            (group_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def user_groups(user_id: int) -> list[dict]:
        db = get_db()
        rows = db.execute(
            "SELECT sg.*, gm.role as my_role, COUNT(gm2.user_id) as member_count "
            "FROM study_groups sg "
            "JOIN group_members gm ON sg.id = gm.group_id AND gm.user_id = ? "
            "LEFT JOIN group_members gm2 ON sg.id = gm2.group_id "
            "GROUP BY sg.id ORDER BY sg.created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


class ChallengeStoreDB:
    """Manage group challenges."""

    @staticmethod
    def create(group_id: int, challenger_id: int, title: str, subject: str = "", config: dict | None = None, expires_hours: int = 48) -> int:
        db = get_db()
        now = datetime.now()
        expires = (now + timedelta(hours=expires_hours)).isoformat()
        cur = db.execute(
            "INSERT INTO challenges (group_id, challenger_id, title, subject, config, status, created_at, expires_at) "
            "VALUES (?, ?, ?, ?, ?, 'open', ?, ?)",
            (group_id, challenger_id, title, subject, json.dumps(config or {}), now.isoformat(), expires),
        )
        db.commit()
        return cur.lastrowid

    @staticmethod
    def get(challenge_id: int) -> dict | None:
        db = get_db()
        row = db.execute("SELECT * FROM challenges WHERE id = ?", (challenge_id,)).fetchone()
        if not row:
            return None
        result = dict(row)
        result["config"] = json.loads(result.get("config", "{}"))
        return result

    @staticmethod
    def group_challenges(group_id: int) -> list[dict]:
        db = get_db()
        rows = db.execute(
            "SELECT ch.*, u.name as challenger_name, "
            "COUNT(cp.user_id) as participant_count "
            "FROM challenges ch "
            "JOIN users u ON ch.challenger_id = u.id "
            "LEFT JOIN challenge_participants cp ON ch.id = cp.challenge_id "
            "WHERE ch.group_id = ? GROUP BY ch.id ORDER BY ch.created_at DESC",
            (group_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def submit_score(challenge_id: int, user_id: int, score: float) -> bool:
        db = get_db()
        try:
            db.execute(
                "INSERT OR REPLACE INTO challenge_participants (challenge_id, user_id, score, completed_at) "
                "VALUES (?, ?, ?, ?)",
                (challenge_id, user_id, score, datetime.now().isoformat()),
            )
            db.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def leaderboard(challenge_id: int) -> list[dict]:
        db = get_db()
        rows = db.execute(
            "SELECT cp.*, u.name FROM challenge_participants cp "
            "JOIN users u ON cp.user_id = u.id "
            "WHERE cp.challenge_id = ? ORDER BY cp.score DESC",
            (challenge_id,),
        ).fetchall()
        return [dict(r) for r in rows]


class LeaderboardStoreDB:
    """Global / group / school leaderboard."""

    @staticmethod
    def get(scope: str = "global", scope_id: int = 0, period: str = "all", limit: int = 50) -> list[dict]:
        db = get_db()
        # Real-time leaderboard from gamification table
        if scope == "global":
            rows = db.execute(
                "SELECT u.id as user_id, u.name, g.total_xp as xp "
                "FROM gamification g JOIN users u ON g.user_id = u.id "
                "ORDER BY g.total_xp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        elif scope == "group":
            rows = db.execute(
                "SELECT u.id as user_id, u.name, g.total_xp as xp "
                "FROM group_members gm "
                "JOIN users u ON gm.user_id = u.id "
                "JOIN gamification g ON g.user_id = u.id "
                "WHERE gm.group_id = ? ORDER BY g.total_xp DESC LIMIT ?",
                (scope_id, limit),
            ).fetchall()
        elif scope == "school":
            rows = db.execute(
                "SELECT u.id as user_id, u.name, g.total_xp as xp "
                "FROM class_members cm "
                "JOIN classes c ON cm.class_id = c.id "
                "JOIN users u ON cm.user_id = u.id "
                "JOIN gamification g ON g.user_id = u.id "
                "WHERE c.school_id = ? GROUP BY u.id ORDER BY g.total_xp DESC LIMIT ?",
                (scope_id, limit),
            ).fetchall()
        else:
            rows = []
        result = []
        for i, r in enumerate(rows, 1):
            entry = dict(r)
            entry["rank"] = i
            result.append(entry)
        return result


# ── Push Subscriptions ───────────────────────────────────────────────


class PushSubscriptionStoreDB:
    """Manage web push subscriptions."""

    @staticmethod
    def subscribe(user_id: int, endpoint: str, p256dh: str, auth: str):
        db = get_db()
        db.execute(
            "INSERT OR REPLACE INTO push_subscriptions (user_id, endpoint, p256dh, auth, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, endpoint, p256dh, auth, datetime.now().isoformat()),
        )
        db.commit()

    @staticmethod
    def unsubscribe(endpoint: str):
        db = get_db()
        db.execute("DELETE FROM push_subscriptions WHERE endpoint = ?", (endpoint,))
        db.commit()

    @staticmethod
    def get_for_user(user_id: int) -> list[dict]:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM push_subscriptions WHERE user_id = ?", (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]


# ── Community Papers ─────────────────────────────────────────────────


class CommunityPaperStoreDB:
    """Manage community-uploaded past papers."""

    @staticmethod
    def create(uploader_id: int, title: str, subject: str = "", level: str = "",
               year: int = 0, session: str = "", paper_number: int = 0,
               questions: list | None = None) -> int:
        db = get_db()
        cur = db.execute(
            "INSERT INTO community_papers (uploader_id, title, subject, level, year, session, "
            "paper_number, questions, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (uploader_id, title, subject, level, year, session, paper_number,
             json.dumps(questions or []), datetime.now().isoformat()),
        )
        db.commit()
        return cur.lastrowid

    @staticmethod
    def list_papers(subject: str = "", level: str = "", approved_only: bool = True,
                    limit: int = 50, offset: int = 0) -> list[dict]:
        db = get_db()
        conditions = []
        params: list = []
        if approved_only:
            conditions.append("approved = 1")
        if subject:
            conditions.append("subject = ?")
            params.append(subject)
        if level:
            conditions.append("level = ?")
            params.append(level)
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        params.extend([limit, offset])
        rows = db.execute(
            f"SELECT cp.*, u.name as uploader_name, "
            f"COALESCE(AVG(pr.rating), 0) as avg_rating, "
            f"COUNT(DISTINCT pr.user_id) as rating_count "
            f"FROM community_papers cp "
            f"JOIN users u ON cp.uploader_id = u.id "
            f"LEFT JOIN paper_ratings pr ON cp.id = pr.paper_id "
            f"{where} GROUP BY cp.id ORDER BY cp.created_at DESC LIMIT ? OFFSET ?",
            params,
        ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def get(paper_id: int) -> dict | None:
        db = get_db()
        row = db.execute("SELECT * FROM community_papers WHERE id = ?", (paper_id,)).fetchone()
        if not row:
            return None
        result = dict(row)
        result["questions"] = json.loads(result.get("questions", "[]"))
        return result

    @staticmethod
    def rate(paper_id: int, user_id: int, rating: int):
        db = get_db()
        db.execute(
            "INSERT OR REPLACE INTO paper_ratings (paper_id, user_id, rating, created_at) "
            "VALUES (?, ?, ?, ?)",
            (paper_id, user_id, max(1, min(5, rating)), datetime.now().isoformat()),
        )
        db.commit()

    @staticmethod
    def report(paper_id: int, user_id: int, reason: str):
        db = get_db()
        db.execute(
            "INSERT INTO paper_reports (paper_id, user_id, reason, created_at) VALUES (?, ?, ?, ?)",
            (paper_id, user_id, reason, datetime.now().isoformat()),
        )
        db.commit()

    @staticmethod
    def approve(paper_id: int):
        db = get_db()
        db.execute("UPDATE community_papers SET approved = 1 WHERE id = ?", (paper_id,))
        db.commit()

    @staticmethod
    def increment_downloads(paper_id: int):
        db = get_db()
        db.execute("UPDATE community_papers SET download_count = download_count + 1 WHERE id = ?", (paper_id,))
        db.commit()


# ── Student Ability (Adaptive) ───────────────────────────────────────


class StudentAbilityStoreDB:
    """Track student ability per subject/topic for adaptive difficulty."""

    def __init__(self, user_id: int):
        self.user_id = user_id

    def get_theta(self, subject: str, topic: str) -> dict:
        db = get_db()
        row = db.execute(
            "SELECT * FROM student_ability WHERE user_id = ? AND subject = ? AND topic = ?",
            (self.user_id, subject, topic),
        ).fetchone()
        if row:
            return dict(row)
        return {"theta": 0.0, "uncertainty": 1.0, "attempts": 0}

    def update_theta(self, subject: str, topic: str, theta: float, uncertainty: float, attempts: int):
        db = get_db()
        db.execute(
            "INSERT INTO student_ability (user_id, subject, topic, theta, uncertainty, attempts, last_updated) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, subject, topic) DO UPDATE SET "
            "theta = excluded.theta, uncertainty = excluded.uncertainty, "
            "attempts = excluded.attempts, last_updated = excluded.last_updated",
            (self.user_id, subject, topic, theta, uncertainty, attempts, datetime.now().isoformat()),
        )
        db.commit()

    def get_profile(self, subject: str) -> list[dict]:
        db = get_db()
        rows = db.execute(
            "SELECT topic, theta, uncertainty, attempts FROM student_ability "
            "WHERE user_id = ? AND subject = ? ORDER BY topic",
            (self.user_id, subject),
        ).fetchall()
        return [dict(r) for r in rows]


# ── Exam Sessions ────────────────────────────────────────────────────


class ExamSessionStoreDB:
    """Track full exam simulation sessions."""

    def __init__(self, user_id: int):
        self.user_id = user_id

    def create(self, subject: str, level: str, paper_number: int,
               duration_minutes: int, questions: list) -> int:
        db = get_db()
        cur = db.execute(
            "INSERT INTO exam_sessions (user_id, subject, level, paper_number, "
            "duration_minutes, started_at, questions) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (self.user_id, subject, level, paper_number, duration_minutes,
             datetime.now().isoformat(), json.dumps(questions)),
        )
        db.commit()
        return cur.lastrowid

    def complete(self, session_id: int, answers: list, earned_marks: int,
                 total_marks: int, grade: int):
        db = get_db()
        db.execute(
            "UPDATE exam_sessions SET completed_at = ?, answers = ?, "
            "earned_marks = ?, total_marks = ?, grade = ? WHERE id = ? AND user_id = ?",
            (datetime.now().isoformat(), json.dumps(answers), earned_marks,
             total_marks, grade, session_id, self.user_id),
        )
        db.commit()

    def get(self, session_id: int) -> dict | None:
        db = get_db()
        row = db.execute(
            "SELECT * FROM exam_sessions WHERE id = ? AND user_id = ?",
            (session_id, self.user_id),
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["questions"] = json.loads(result.get("questions", "[]"))
        result["answers"] = json.loads(result.get("answers", "[]"))
        return result

    def list_sessions(self, limit: int = 20) -> list[dict]:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM exam_sessions WHERE user_id = ? ORDER BY started_at DESC LIMIT ?",
            (self.user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


# ── Tutor Conversations ──────────────────────────────────────────────


class TutorConversationStoreDB:
    """Manage AI tutor conversation history."""

    def __init__(self, user_id: int):
        self.user_id = user_id

    def create(self, subject: str = "", topic: str = "") -> int:
        db = get_db()
        now = datetime.now().isoformat()
        cur = db.execute(
            "INSERT INTO tutor_conversations (user_id, subject, topic, messages, created_at, updated_at) "
            "VALUES (?, ?, ?, '[]', ?, ?)",
            (self.user_id, subject, topic, now, now),
        )
        db.commit()
        return cur.lastrowid

    def get(self, conv_id: int) -> dict | None:
        db = get_db()
        row = db.execute(
            "SELECT * FROM tutor_conversations WHERE id = ? AND user_id = ?",
            (conv_id, self.user_id),
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["messages"] = json.loads(result.get("messages", "[]"))
        return result

    def add_message(self, conv_id: int, role: str, content: str):
        db = get_db()
        row = db.execute(
            "SELECT messages FROM tutor_conversations WHERE id = ? AND user_id = ?",
            (conv_id, self.user_id),
        ).fetchone()
        if not row:
            return
        messages = json.loads(row["messages"])
        messages.append({"role": role, "content": content, "timestamp": datetime.now().isoformat()})
        db.execute(
            "UPDATE tutor_conversations SET messages = ?, updated_at = ? WHERE id = ?",
            (json.dumps(messages), datetime.now().isoformat(), conv_id),
        )
        db.commit()

    def list_conversations(self, limit: int = 20) -> list[dict]:
        db = get_db()
        rows = db.execute(
            "SELECT id, subject, topic, created_at, updated_at FROM tutor_conversations "
            "WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?",
            (self.user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


# ── Shared Flashcard Decks ──────────────────────────────────────────────


class SharedFlashcardDeckDB:
    """Manage shared flashcard decks in the community."""

    @staticmethod
    def share(user_id: int, title: str, subject: str, topic: str = "",
              description: str = "", cards: list | None = None) -> int:
        db = get_db()
        card_list = cards or []
        cur = db.execute(
            "INSERT INTO shared_flashcard_decks "
            "(user_id, title, subject, topic, description, card_count, cards, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, title, subject, topic, description,
             len(card_list), json.dumps(card_list), datetime.now().isoformat()),
        )
        db.commit()
        return cur.lastrowid

    @staticmethod
    def list_decks(subject: str = "", topic: str = "", limit: int = 50) -> list[dict]:
        db = get_db()
        query = (
            "SELECT d.*, u.name as author_name FROM shared_flashcard_decks d "
            "JOIN users u ON d.user_id = u.id WHERE 1=1"
        )
        params: list = []
        if subject:
            query += " AND d.subject = ?"
            params.append(subject)
        if topic:
            query += " AND d.topic LIKE ?"
            params.append(f"%{topic}%")
        query += " ORDER BY d.created_at DESC LIMIT ?"
        params.append(limit)
        rows = db.execute(query, params).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["cards"] = json.loads(d.get("cards", "[]"))
            avg_rating = d["rating_sum"] / d["rating_count"] if d["rating_count"] > 0 else 0
            d["avg_rating"] = round(avg_rating, 1)
            result.append(d)
        return result

    @staticmethod
    def get(deck_id: int) -> dict | None:
        db = get_db()
        row = db.execute(
            "SELECT d.*, u.name as author_name FROM shared_flashcard_decks d "
            "JOIN users u ON d.user_id = u.id WHERE d.id = ?",
            (deck_id,),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["cards"] = json.loads(d.get("cards", "[]"))
        avg_rating = d["rating_sum"] / d["rating_count"] if d["rating_count"] > 0 else 0
        d["avg_rating"] = round(avg_rating, 1)
        return d

    @staticmethod
    def import_deck(deck_id: int, user_id: int) -> int:
        """Import a shared deck's cards into user's personal flashcards. Returns count imported."""
        import uuid
        db = get_db()
        row = db.execute("SELECT cards, subject, topic FROM shared_flashcard_decks WHERE id = ?", (deck_id,)).fetchone()
        if not row:
            return 0
        cards = json.loads(row["cards"])
        now = datetime.now().isoformat()
        count = 0
        for card in cards:
            card_id = str(uuid.uuid4())[:8]
            try:
                db.execute(
                    "INSERT INTO flashcards (id, user_id, front, back, subject, topic, source, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, 'shared_import', ?)",
                    (card_id, user_id, card.get("front", ""), card.get("back", ""),
                     row["subject"], row["topic"], now),
                )
                count += 1
            except Exception:
                pass
        db.execute(
            "UPDATE shared_flashcard_decks SET download_count = download_count + 1 WHERE id = ?",
            (deck_id,),
        )
        db.commit()
        return count


# ── Study Buddy Preferences ──────────────────────────────────────────────


class StudyBuddyDB:
    """Manage study buddy preferences and matching."""

    @staticmethod
    def save_preferences(user_id: int, subjects: list, availability: str = "",
                         timezone: str = "", looking_for: str = "study_partner"):
        db = get_db()
        db.execute(
            "INSERT OR REPLACE INTO study_buddy_preferences "
            "(user_id, subjects, availability, timezone, looking_for, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, json.dumps(subjects), availability, timezone,
             looking_for, datetime.now().isoformat()),
        )
        db.commit()

    @staticmethod
    def get_preferences(user_id: int) -> dict | None:
        db = get_db()
        row = db.execute(
            "SELECT * FROM study_buddy_preferences WHERE user_id = ?", (user_id,),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["subjects"] = json.loads(d.get("subjects", "[]"))
        return d

    @staticmethod
    def find_matches(user_id: int, limit: int = 10) -> list[dict]:
        """Find students with overlapping subjects who are looking for study partners."""
        db = get_db()
        prefs = db.execute(
            "SELECT subjects FROM study_buddy_preferences WHERE user_id = ?", (user_id,),
        ).fetchone()
        if not prefs:
            return []
        my_subjects = set(json.loads(prefs["subjects"]))
        if not my_subjects:
            return []

        rows = db.execute(
            "SELECT sbp.*, u.name FROM study_buddy_preferences sbp "
            "JOIN users u ON sbp.user_id = u.id "
            "WHERE sbp.user_id != ? "
            "ORDER BY sbp.updated_at DESC LIMIT ?",
            (user_id, limit * 3),
        ).fetchall()

        matches = []
        for r in rows:
            their_subjects = set(json.loads(r["subjects"]))
            overlap = my_subjects & their_subjects
            if overlap:
                matches.append({
                    "user_id": r["user_id"],
                    "name": r["name"],
                    "common_subjects": list(overlap),
                    "availability": r["availability"],
                    "timezone": r["timezone"],
                    "looking_for": r["looking_for"],
                })
            if len(matches) >= limit:
                break
        return matches
