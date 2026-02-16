"""
Student Profile, Writing Style Manager, Grade Detail Log, Activity Tracking & Spaced Repetition

Persists student profile (name, subjects, exam session, targets), writing style
analysis, activity logs, and spaced repetition schedules to session_data/ as JSON files.
"""

from __future__ import annotations

import json
import math
import secrets
from dataclasses import dataclass, field, asdict
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

from subject_config import IB_SUBJECTS  # noqa: F401 — re-exported for backward compat

SESSION_DIR = Path(__file__).parent / "session_data"
SESSION_DIR.mkdir(exist_ok=True)

PROFILE_PATH = SESSION_DIR / "profile.json"
WRITING_PROFILE_PATH = SESSION_DIR / "writing_profile.json"
GRADE_DETAIL_PATH = SESSION_DIR / "grade_detail.json"
TOPIC_PROGRESS_PATH = SESSION_DIR / "topic_progress.json"
PARENT_CONFIG_PATH = SESSION_DIR / "parent_config.json"
ACTIVITY_LOG_PATH = SESSION_DIR / "activity_log.json"
REVIEW_SCHEDULE_PATH = SESSION_DIR / "review_schedule.json"
GAMIFICATION_PATH = SESSION_DIR / "gamification.json"
FLASHCARD_PATH = SESSION_DIR / "flashcards.json"
MISCONCEPTION_PATH = SESSION_DIR / "misconceptions.json"
MOCK_REPORT_PATH = SESSION_DIR / "mock_reports.json"
NOTIFICATION_PATH = SESSION_DIR / "notifications.json"
SHARED_QUESTIONS_PATH = SESSION_DIR / "shared_questions.json"


@dataclass
class SubjectEntry:
    name: str
    level: str  # "HL" or "SL"
    target_grade: int = 5  # 1-7


@dataclass
class StudentProfile:
    name: str
    subjects: list[SubjectEntry]
    exam_session: str  # e.g. "May 2026"
    target_total_points: int = 35  # 24-45
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def save(self) -> None:
        data = {
            "name": self.name,
            "subjects": [
                {"name": s.name, "level": s.level, "target_grade": s.target_grade}
                for s in self.subjects
            ],
            "exam_session": self.exam_session,
            "target_total_points": self.target_total_points,
            "created_at": self.created_at,
        }
        PROFILE_PATH.write_text(json.dumps(data, indent=2))

    @staticmethod
    def load() -> Optional[StudentProfile]:
        if not PROFILE_PATH.exists():
            return None
        try:
            data = json.loads(PROFILE_PATH.read_text())
            return StudentProfile(
                name=data["name"],
                subjects=[
                    SubjectEntry(
                        name=s["name"],
                        level=s["level"],
                        target_grade=s.get("target_grade", 5),
                    )
                    for s in data["subjects"]
                ],
                exam_session=data["exam_session"],
                target_total_points=data.get("target_total_points", 35),
                created_at=data.get("created_at", ""),
            )
        except (json.JSONDecodeError, KeyError):
            return None

    @staticmethod
    def exists() -> bool:
        return PROFILE_PATH.exists()

    def subject_key(self, name: str) -> str:
        """Convert display name to the key format used by rag_engine/ingest."""
        return name.lower().split(":")[0].strip().replace(" ", "_")

    def exam_countdown(self) -> dict:
        """Return {days, urgency, exam_date} until next IB exam session."""
        today = date.today()
        try:
            parts = self.exam_session.split()
            month_str = parts[0].lower()
            year = int(parts[1])
            if month_str.startswith("may"):
                exam_date = date(year, 5, 1)
            else:
                exam_date = date(year, 11, 1)
        except (ValueError, IndexError):
            year = today.year if today.month < 5 else today.year + 1
            exam_date = date(year, 5, 1)

        days = (exam_date - today).days
        if days < 0:
            days = 0

        if days > 120:
            urgency = "calm"
        elif days > 60:
            urgency = "focused"
        elif days > 21:
            urgency = "urgent"
        else:
            urgency = "critical"

        return {
            "days": days,
            "urgency": urgency,
            "exam_date": exam_date.isoformat(),
        }

    def compute_gaps(self, grade_log: GradeDetailLog) -> list[dict]:
        """Per-subject {subject, level, target, predicted, gap, status} sorted by biggest gap."""
        subject_stats = grade_log.subject_stats()
        gaps = []
        for s in self.subjects:
            stats = subject_stats.get(s.name, None)
            if stats and stats["count"] > 0:
                predicted = round(stats["avg_grade"])
                gap = s.target_grade - predicted
                if gap <= 0:
                    status = "on_track"
                elif gap == 1:
                    status = "close"
                else:
                    status = "behind"
            else:
                predicted = 0
                gap = 0
                status = "no_data"

            gaps.append({
                "subject": s.name,
                "level": s.level,
                "target": s.target_grade,
                "predicted": predicted,
                "gap": gap,
                "status": status,
            })

        gaps.sort(key=lambda g: (-g["gap"] if g["status"] != "no_data" else -999))
        return gaps

    def compute_predicted_total(self, grade_log: GradeDetailLog) -> int:
        """Sum of predicted grades across subjects."""
        subject_stats = grade_log.subject_stats()
        total = 0
        for s in self.subjects:
            stats = subject_stats.get(s.name, None)
            if stats and stats["count"] > 0:
                total += round(stats["avg_grade"])
            else:
                total += s.target_grade
        return total


# ── Topic Progress Tracking ────────────────────────────────────────────

@dataclass
class TopicAttempt:
    subtopic: str
    attempts: int = 0
    avg_percentage: float = 0.0
    last_practiced: str = ""


@dataclass
class TopicProgress:
    """Tracks which syllabus subtopics a student has practiced per subject."""
    subject: str
    topics: dict[str, list[TopicAttempt]] = field(default_factory=dict)
    # topics is {topic_id: [TopicAttempt, ...]}

    def record(self, topic_id: str, subtopic: str, percentage: float) -> None:
        if topic_id not in self.topics:
            self.topics[topic_id] = []

        # Find or create attempt record
        attempt = None
        for a in self.topics[topic_id]:
            if a.subtopic == subtopic:
                attempt = a
                break
        if not attempt:
            attempt = TopicAttempt(subtopic=subtopic)
            self.topics[topic_id].append(attempt)

        # Update running average
        old_total = attempt.avg_percentage * attempt.attempts
        attempt.attempts += 1
        attempt.avg_percentage = round((old_total + percentage) / attempt.attempts, 1)
        attempt.last_practiced = datetime.now().isoformat()

    def coverage_for_topic(self, topic_id: str, total_subtopics: int) -> float:
        """Return 0-100 coverage percentage for a given topic."""
        if total_subtopics == 0:
            return 0
        practiced = len(self.topics.get(topic_id, []))
        return round(practiced / total_subtopics * 100, 1)

    def overall_coverage(self, syllabus_topics: list) -> float:
        """Return overall syllabus coverage as 0-100%."""
        total_subtopics = 0
        practiced_subtopics = 0
        for topic in syllabus_topics:
            total_subtopics += len(topic.subtopics)
            practiced_subtopics += len(self.topics.get(topic.id, []))
        if total_subtopics == 0:
            return 0
        return round(practiced_subtopics / total_subtopics * 100, 1)


class TopicProgressStore:
    """Manages TopicProgress for all subjects. Persists to JSON."""

    def __init__(self) -> None:
        self._data: dict[str, TopicProgress] = {}
        self._load()

    def get(self, subject: str) -> TopicProgress:
        if subject not in self._data:
            self._data[subject] = TopicProgress(subject=subject)
        return self._data[subject]

    def record(self, subject: str, topic_id: str, subtopic: str, percentage: float) -> None:
        tp = self.get(subject)
        tp.record(topic_id, subtopic, percentage)
        self._save()

    def _save(self) -> None:
        data = {}
        for subject, tp in self._data.items():
            topics_dict = {}
            for topic_id, attempts in tp.topics.items():
                topics_dict[topic_id] = [
                    {"subtopic": a.subtopic, "attempts": a.attempts,
                     "avg_percentage": a.avg_percentage, "last_practiced": a.last_practiced}
                    for a in attempts
                ]
            data[subject] = topics_dict
        TOPIC_PROGRESS_PATH.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        if not TOPIC_PROGRESS_PATH.exists():
            return
        try:
            data = json.loads(TOPIC_PROGRESS_PATH.read_text())
            for subject, topics_dict in data.items():
                tp = TopicProgress(subject=subject)
                for topic_id, attempts_data in topics_dict.items():
                    tp.topics[topic_id] = [
                        TopicAttempt(
                            subtopic=a["subtopic"],
                            attempts=a.get("attempts", 0),
                            avg_percentage=a.get("avg_percentage", 0),
                            last_practiced=a.get("last_practiced", ""),
                        )
                        for a in attempts_data
                    ]
                self._data[subject] = tp
        except (json.JSONDecodeError, KeyError, TypeError):
            pass


# ── Grade Detail Log ───────────────────────────────────────────────────

@dataclass
class GradeDetailEntry:
    subject: str
    subject_display: str
    level: str
    command_term: str
    grade: int
    percentage: int
    mark_earned: int
    mark_total: int
    strengths: list[str]
    improvements: list[str]
    examiner_tip: str
    topic: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class GradeDetailLog:
    """Parallel grade log that enriches each grade with subject + command_term metadata."""

    def __init__(self) -> None:
        self.entries: list[GradeDetailEntry] = []
        self._load()

    def add(self, entry: GradeDetailEntry) -> None:
        self.entries.append(entry)
        self._save()

    def by_subject(self, subject_display: str) -> list[GradeDetailEntry]:
        return [e for e in self.entries if e.subject_display == subject_display]

    def by_command_term(self, command_term: str) -> list[GradeDetailEntry]:
        ct_lower = command_term.lower()
        return [e for e in self.entries if e.command_term.lower() == ct_lower]

    def command_term_stats(self) -> dict:
        ct_data: dict[str, list[GradeDetailEntry]] = {}
        for e in self.entries:
            ct = e.command_term or "Unknown"
            ct_data.setdefault(ct, []).append(e)

        stats = {}
        for ct, entries in ct_data.items():
            grades = [e.grade for e in entries]
            pcts = [e.percentage for e in entries]
            stats[ct] = {
                "count": len(entries),
                "avg_grade": round(sum(grades) / len(grades), 1) if grades else 0,
                "avg_percentage": round(sum(pcts) / len(pcts), 1) if pcts else 0,
            }
        return stats

    def subject_stats(self) -> dict:
        subj_data: dict[str, list[GradeDetailEntry]] = {}
        for e in self.entries:
            subj_data.setdefault(e.subject_display, []).append(e)

        stats = {}
        for subj, entries in subj_data.items():
            grades = [e.grade for e in entries]
            pcts = [e.percentage for e in entries]
            stats[subj] = {
                "count": len(entries),
                "avg_grade": round(sum(grades) / len(grades), 1) if grades else 0,
                "avg_percentage": round(sum(pcts) / len(pcts), 1) if pcts else 0,
            }
        return stats

    def recent(self, n: int = 5) -> list[GradeDetailEntry]:
        return list(reversed(self.entries[-n:]))

    def _save(self) -> None:
        data = []
        for e in self.entries:
            data.append({
                "subject": e.subject,
                "subject_display": e.subject_display,
                "level": e.level,
                "command_term": e.command_term,
                "grade": e.grade,
                "percentage": e.percentage,
                "mark_earned": e.mark_earned,
                "mark_total": e.mark_total,
                "strengths": e.strengths,
                "improvements": e.improvements,
                "examiner_tip": e.examiner_tip,
                "topic": e.topic,
                "timestamp": e.timestamp,
            })
        GRADE_DETAIL_PATH.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        if not GRADE_DETAIL_PATH.exists():
            return
        try:
            data = json.loads(GRADE_DETAIL_PATH.read_text())
            for entry in data:
                self.entries.append(GradeDetailEntry(
                    subject=entry["subject"],
                    subject_display=entry.get("subject_display", entry["subject"]),
                    level=entry.get("level", ""),
                    command_term=entry.get("command_term", ""),
                    grade=entry["grade"],
                    percentage=entry["percentage"],
                    mark_earned=entry["mark_earned"],
                    mark_total=entry["mark_total"],
                    strengths=entry.get("strengths", []),
                    improvements=entry.get("improvements", []),
                    examiner_tip=entry.get("examiner_tip", ""),
                    topic=entry.get("topic", ""),
                    timestamp=entry.get("timestamp", ""),
                ))
        except (json.JSONDecodeError, KeyError):
            pass


# ── Parent Portal Config ───────────────────────────────────────────────

@dataclass
class ParentConfig:
    enabled: bool = False
    token: str = ""
    created_at: str = ""
    student_display_name: str = ""
    show_subject_grades: bool = True
    show_recent_activity: bool = True
    show_study_consistency: bool = True
    show_command_term_stats: bool = False
    show_insights: bool = True
    show_exam_countdown: bool = True

    def generate_token(self) -> str:
        self.token = secrets.token_hex(16)
        self.created_at = datetime.now().isoformat()
        return self.token

    def save(self) -> None:
        PARENT_CONFIG_PATH.write_text(json.dumps(asdict(self), indent=2))

    @staticmethod
    def load() -> ParentConfig:
        if not PARENT_CONFIG_PATH.exists():
            return ParentConfig()
        try:
            data = json.loads(PARENT_CONFIG_PATH.read_text())
            return ParentConfig(**data)
        except (json.JSONDecodeError, KeyError, TypeError):
            return ParentConfig()


# ── Activity Logging ───────────────────────────────────────────────────

@dataclass
class ActivityEntry:
    date: str               # "2026-02-16"
    subject: str
    questions_attempted: int
    questions_answered: int
    avg_grade: float
    avg_percentage: float
    duration_minutes: int
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ActivityLog:
    """Tracks per-session activity for consistency metrics."""

    def __init__(self) -> None:
        self.entries: list[ActivityEntry] = []
        self._load()

    def record(self, subject: str, grade: float, percentage: float) -> None:
        today = date.today().isoformat()
        # Find or create today's entry for this subject
        entry = None
        for e in self.entries:
            if e.date == today and e.subject == subject:
                entry = e
                break
        if entry:
            old_total_grade = entry.avg_grade * entry.questions_answered
            old_total_pct = entry.avg_percentage * entry.questions_answered
            entry.questions_attempted += 1
            entry.questions_answered += 1
            entry.avg_grade = round((old_total_grade + grade) / entry.questions_answered, 2)
            entry.avg_percentage = round((old_total_pct + percentage) / entry.questions_answered, 1)
            entry.timestamp = datetime.now().isoformat()
        else:
            self.entries.append(ActivityEntry(
                date=today,
                subject=subject,
                questions_attempted=1,
                questions_answered=1,
                avg_grade=grade,
                avg_percentage=percentage,
                duration_minutes=0,
            ))
        self._save()

    def days_active_last_n(self, n: int = 30) -> int:
        cutoff = (date.today() - timedelta(days=n)).isoformat()
        active_dates = {e.date for e in self.entries if e.date >= cutoff}
        return len(active_dates)

    def streak(self) -> int:
        """Current consecutive days active streak."""
        active_dates = sorted({e.date for e in self.entries}, reverse=True)
        if not active_dates:
            return 0
        today = date.today()
        # Allow today or yesterday as the start
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
        """Return summary per week for the last n weeks."""
        today = date.today()
        summaries = []
        for w in range(n_weeks):
            week_start = today - timedelta(days=today.weekday() + 7 * w)
            week_end = week_start + timedelta(days=6)
            week_entries = [
                e for e in self.entries
                if week_start.isoformat() <= e.date <= week_end.isoformat()
            ]
            total_questions = sum(e.questions_answered for e in week_entries)
            subjects = list({e.subject for e in week_entries})
            avg_grade = 0
            if week_entries:
                grades = [e.avg_grade for e in week_entries]
                avg_grade = round(sum(grades) / len(grades), 1)
            summaries.append({
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
                "total_questions": total_questions,
                "subjects_studied": subjects,
                "avg_grade": avg_grade,
                "days_active": len({e.date for e in week_entries}),
            })
        return summaries

    def daily_heatmap(self, n_days: int = 90) -> list[dict]:
        """Return {date, count} for the last n_days for heatmap display."""
        today = date.today()
        date_counts: dict[str, int] = {}
        for e in self.entries:
            if e.date not in date_counts:
                date_counts[e.date] = 0
            date_counts[e.date] += e.questions_answered

        heatmap = []
        for i in range(n_days):
            d = (today - timedelta(days=n_days - 1 - i)).isoformat()
            heatmap.append({"date": d, "count": date_counts.get(d, 0)})
        return heatmap

    def recent_activity(self, n: int = 10) -> list[dict]:
        """Return the most recent activity entries as dicts."""
        sorted_entries = sorted(self.entries, key=lambda e: e.timestamp, reverse=True)
        result = []
        for e in sorted_entries[:n]:
            result.append({
                "date": e.date,
                "subject": e.subject,
                "questions": e.questions_answered,
                "avg_grade": e.avg_grade,
                "avg_percentage": e.avg_percentage,
            })
        return result

    def _save(self) -> None:
        data = [asdict(e) for e in self.entries]
        ACTIVITY_LOG_PATH.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        if not ACTIVITY_LOG_PATH.exists():
            return
        try:
            data = json.loads(ACTIVITY_LOG_PATH.read_text())
            for entry in data:
                self.entries.append(ActivityEntry(
                    date=entry["date"],
                    subject=entry["subject"],
                    questions_attempted=entry.get("questions_attempted", 0),
                    questions_answered=entry.get("questions_answered", 0),
                    avg_grade=entry.get("avg_grade", 0),
                    avg_percentage=entry.get("avg_percentage", 0),
                    duration_minutes=entry.get("duration_minutes", 0),
                    timestamp=entry.get("timestamp", ""),
                ))
        except (json.JSONDecodeError, KeyError, TypeError):
            pass


# ── Spaced Repetition (SM-2 Algorithm) ─────────────────────────────────

@dataclass
class ReviewItem:
    subject: str
    topic: str
    command_term: str
    last_reviewed: str      # ISO date
    next_review: str        # ISO date
    interval_days: int = 1
    ease_factor: float = 2.5
    review_count: int = 0


class ReviewSchedule:
    """SM-2 spaced repetition algorithm for topic+command_term review."""

    def __init__(self) -> None:
        self.items: list[ReviewItem] = []
        self._load()

    def record_review(self, subject: str, topic: str, command_term: str, grade: int) -> None:
        """Record a review. Grade 1-7 is mapped to SM-2 quality 0-5."""
        quality = self._grade_to_quality(grade)
        item = self._find_or_create(subject, topic, command_term)

        item.review_count += 1
        item.last_reviewed = date.today().isoformat()

        # SM-2 algorithm
        if quality < 3:
            # Failed review — reset interval
            item.interval_days = 1
        else:
            if item.review_count == 1:
                item.interval_days = 1
            elif item.review_count == 2:
                item.interval_days = 6
            else:
                item.interval_days = max(1, round(item.interval_days * item.ease_factor))

        # Update ease factor
        item.ease_factor = max(
            1.3,
            item.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)),
        )

        item.next_review = (date.today() + timedelta(days=item.interval_days)).isoformat()
        self._save()

    def due_today(self) -> list[ReviewItem]:
        today = date.today().isoformat()
        return [item for item in self.items if item.next_review <= today]

    def due_this_week(self) -> list[ReviewItem]:
        week_end = (date.today() + timedelta(days=7)).isoformat()
        return [item for item in self.items if item.next_review <= week_end]

    def _grade_to_quality(self, grade: int) -> int:
        """Map IB grade (1-7) to SM-2 quality (0-5)."""
        mapping = {7: 5, 6: 4, 5: 3, 4: 2, 3: 1, 2: 0, 1: 0}
        return mapping.get(grade, 2)

    def _find_or_create(self, subject: str, topic: str, command_term: str) -> ReviewItem:
        for item in self.items:
            if item.subject == subject and item.topic == topic and item.command_term == command_term:
                return item
        item = ReviewItem(
            subject=subject,
            topic=topic,
            command_term=command_term,
            last_reviewed=date.today().isoformat(),
            next_review=date.today().isoformat(),
        )
        self.items.append(item)
        return item

    def _save(self) -> None:
        data = [asdict(item) for item in self.items]
        REVIEW_SCHEDULE_PATH.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        if not REVIEW_SCHEDULE_PATH.exists():
            return
        try:
            data = json.loads(REVIEW_SCHEDULE_PATH.read_text())
            for entry in data:
                self.items.append(ReviewItem(
                    subject=entry["subject"],
                    topic=entry["topic"],
                    command_term=entry["command_term"],
                    last_reviewed=entry.get("last_reviewed", ""),
                    next_review=entry.get("next_review", ""),
                    interval_days=entry.get("interval_days", 1),
                    ease_factor=entry.get("ease_factor", 2.5),
                    review_count=entry.get("review_count", 0),
                ))
        except (json.JSONDecodeError, KeyError, TypeError):
            pass


# ── Study Planner ──────────────────────────────────────────────────────

@dataclass
class StudyTask:
    subject: str
    topic: str
    task_type: str  # "practice"|"review"|"ia_work"|"ee_work"|"past_paper"
    duration_minutes: int
    priority: str   # "high"|"medium"|"low"
    completed: bool = False


@dataclass
class DailyPlan:
    date: str
    tasks: list[StudyTask] = field(default_factory=list)
    estimated_minutes: int = 0


@dataclass
class StudyPlan:
    generated_date: str = ""
    exam_date: str = ""
    daily_plans: list[DailyPlan] = field(default_factory=list)

    def save(self) -> None:
        path = SESSION_DIR / "study_plan.json"
        data = {
            "generated_date": self.generated_date,
            "exam_date": self.exam_date,
            "daily_plans": [
                {
                    "date": dp.date,
                    "estimated_minutes": dp.estimated_minutes,
                    "tasks": [asdict(t) for t in dp.tasks],
                }
                for dp in self.daily_plans
            ],
        }
        path.write_text(json.dumps(data, indent=2))

    @staticmethod
    def load() -> Optional[StudyPlan]:
        path = SESSION_DIR / "study_plan.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            plan = StudyPlan(
                generated_date=data.get("generated_date", ""),
                exam_date=data.get("exam_date", ""),
            )
            for dp_data in data.get("daily_plans", []):
                tasks = [
                    StudyTask(**t) for t in dp_data.get("tasks", [])
                ]
                plan.daily_plans.append(DailyPlan(
                    date=dp_data["date"],
                    estimated_minutes=dp_data.get("estimated_minutes", 0),
                    tasks=tasks,
                ))
            return plan
        except (json.JSONDecodeError, KeyError, TypeError):
            return None


@dataclass
class WritingProfile:
    """Stores analysis of a student's writing patterns from their past exams."""
    verbosity: str = ""
    terminology_usage: str = ""
    argument_structure: str = ""
    common_patterns: list[str] = field(default_factory=list)
    summary: str = ""
    analyzed_count: int = 0
    last_updated: str = ""

    def save(self) -> None:
        WRITING_PROFILE_PATH.write_text(json.dumps(asdict(self), indent=2))

    @staticmethod
    def load() -> Optional[WritingProfile]:
        if not WRITING_PROFILE_PATH.exists():
            return None
        try:
            data = json.loads(WRITING_PROFILE_PATH.read_text())
            return WritingProfile(**data)
        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    @staticmethod
    def exists() -> bool:
        return WRITING_PROFILE_PATH.exists()

    def grader_context(self) -> str:
        if not self.summary:
            return ""
        return (
            f"\n\nSTUDENT WRITING PROFILE (personalize feedback based on this):\n"
            f"{self.summary}\n"
            f"Verbosity: {self.verbosity}\n"
            f"Terminology usage: {self.terminology_usage}\n"
            f"Argument structure: {self.argument_structure}\n"
        )


# ── Gamification Engine ───────────────────────────────────────────

BADGE_DEFINITIONS = {
    "first_question": {"name": "First Question", "description": "Answer your first question", "icon": "star"},
    "streak_7": {"name": "7-Day Streak", "description": "Study 7 days in a row", "icon": "fire"},
    "all_subjects": {"name": "All-Rounder", "description": "Practice all your subjects", "icon": "globe"},
    "grade_7_club": {"name": "Grade 7 Club", "description": "Score a Grade 7 on any question", "icon": "trophy"},
    "century": {"name": "Century", "description": "Answer 100 questions", "icon": "hundred"},
    "syllabus_50": {"name": "Half Way There", "description": "Cover 50% of any subject's syllabus", "icon": "map"},
    "mock_complete": {"name": "Mock Master", "description": "Complete an exam simulation", "icon": "clipboard"},
    "flashcard_50": {"name": "Card Shark", "description": "Review 50 flashcards", "icon": "cards"},
    "streak_30": {"name": "Monthly Warrior", "description": "Study 30 days in a row", "icon": "medal"},
}

XP_AWARDS = {
    "answer_question": 10,
    "grade_5_bonus": 5,
    "grade_7_bonus": 15,
    "daily_goal_complete": 25,
    "streak_7_milestone": 30,
    "review_flashcard": 8,
    "complete_planner_task": 5,
    "upload_document": 10,
}


@dataclass
class GamificationProfile:
    total_xp: int = 0
    daily_xp_today: int = 0
    daily_xp_date: str = ""
    daily_goal_xp: int = 100
    current_streak: int = 0
    longest_streak: int = 0
    badges: list[str] = field(default_factory=list)  # badge IDs
    streak_freeze_available: int = 0
    streak_freeze_used_date: str = ""
    total_questions_answered: int = 0
    total_flashcards_reviewed: int = 0
    subjects_practiced: list[str] = field(default_factory=list)

    @property
    def level(self) -> int:
        return int(math.sqrt(self.total_xp / 50)) + 1

    @property
    def xp_for_current_level(self) -> int:
        """XP needed to reach current level."""
        return (self.level - 1) ** 2 * 50

    @property
    def xp_for_next_level(self) -> int:
        """XP needed to reach next level."""
        return self.level ** 2 * 50

    @property
    def xp_progress_pct(self) -> int:
        """Percentage progress toward next level."""
        level_start = self.xp_for_current_level
        level_end = self.xp_for_next_level
        level_range = level_end - level_start
        if level_range <= 0:
            return 100
        return min(100, int((self.total_xp - level_start) / level_range * 100))

    @property
    def daily_goal_pct(self) -> int:
        return min(100, int(self.daily_xp_today / self.daily_goal_xp * 100)) if self.daily_goal_xp > 0 else 0

    def award_xp(self, amount: int, reason: str = "") -> dict:
        """Award XP and check for level up, daily goal, and badges."""
        today = date.today().isoformat()
        if self.daily_xp_date != today:
            self.daily_xp_today = 0
            self.daily_xp_date = today

        old_level = self.level
        self.total_xp += amount
        self.daily_xp_today += amount
        new_level = self.level

        result = {"xp_earned": amount, "total_xp": self.total_xp, "new_badges": []}

        if new_level > old_level:
            result["level_up"] = new_level

        # Daily goal check
        if self.daily_xp_today >= self.daily_goal_xp and (self.daily_xp_today - amount) < self.daily_goal_xp:
            self.total_xp += XP_AWARDS["daily_goal_complete"]
            result["daily_goal_complete"] = True

        self.save()
        return result

    def check_badges(self, grade: int = 0, subjects_count: int = 0,
                     syllabus_coverage: float = 0, mock_complete: bool = False) -> list[str]:
        """Check and award new badges. Returns list of newly earned badge IDs."""
        new_badges = []

        checks = [
            ("first_question", self.total_questions_answered >= 1),
            ("streak_7", self.current_streak >= 7),
            ("streak_30", self.current_streak >= 30),
            ("grade_7_club", grade >= 7),
            ("century", self.total_questions_answered >= 100),
            ("all_subjects", subjects_count > 0 and len(self.subjects_practiced) >= subjects_count),
            ("syllabus_50", syllabus_coverage >= 50),
            ("mock_complete", mock_complete),
            ("flashcard_50", self.total_flashcards_reviewed >= 50),
        ]

        for badge_id, condition in checks:
            if condition and badge_id not in self.badges:
                self.badges.append(badge_id)
                new_badges.append(badge_id)

        if new_badges:
            self.save()
        return new_badges

    def update_streak(self, activity_log: ActivityLog) -> None:
        """Sync streak from activity log, applying streak freeze if needed."""
        active_dates = sorted({e.date for e in activity_log.entries}, reverse=True)
        if not active_dates:
            self.current_streak = 0
            return

        today = date.today()
        latest = date.fromisoformat(active_dates[0])
        gap = (today - latest).days

        if gap <= 1:
            # Active today or yesterday — count streak
            self.current_streak = activity_log.streak()
        elif gap == 2 and self.streak_freeze_available > 0:
            # Missed yesterday, use freeze
            self.streak_freeze_available -= 1
            self.streak_freeze_used_date = (today - timedelta(days=1)).isoformat()
            self.current_streak = activity_log.streak() + 1  # Keep the streak going
        else:
            self.current_streak = 0

        # Award streak freeze every 7 days
        if self.current_streak > 0 and self.current_streak % 7 == 0:
            self.streak_freeze_available = min(self.streak_freeze_available + 1, 3)

        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak

        self.save()

    def save(self) -> None:
        GAMIFICATION_PATH.write_text(json.dumps(asdict(self), indent=2))

    @staticmethod
    def load() -> GamificationProfile:
        if not GAMIFICATION_PATH.exists():
            return GamificationProfile()
        try:
            data = json.loads(GAMIFICATION_PATH.read_text())
            return GamificationProfile(**data)
        except (json.JSONDecodeError, KeyError, TypeError):
            return GamificationProfile()


# ── Flashcard System ──────────────────────────────────────────────

@dataclass
class Flashcard:
    id: str
    front: str
    back: str
    subject: str
    topic: str = ""
    source: str = ""  # "auto_grading" | "auto_weakness" | "command_term" | "manual"
    interval_days: int = 1
    ease_factor: float = 2.5
    next_review: str = ""  # ISO date
    last_reviewed: str = ""
    review_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class FlashcardDeck:
    """SM-2 flashcard system with auto-generation from grading results."""

    def __init__(self) -> None:
        self.cards: list[Flashcard] = []
        self._load()

    def add(self, card: Flashcard) -> None:
        if not card.id:
            card.id = f"fc_{len(self.cards)}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        if not card.next_review:
            card.next_review = date.today().isoformat()
        self.cards.append(card)
        self._save()

    def delete(self, card_id: str) -> bool:
        before = len(self.cards)
        self.cards = [c for c in self.cards if c.id != card_id]
        if len(self.cards) < before:
            self._save()
            return True
        return False

    def due_today(self) -> list[Flashcard]:
        today = date.today().isoformat()
        return [c for c in self.cards if c.next_review <= today]

    def due_count(self) -> int:
        return len(self.due_today())

    def by_subject(self, subject: str) -> list[Flashcard]:
        return [c for c in self.cards if c.subject == subject]

    def review(self, card_id: str, rating: int) -> None:
        """Rate a card: 1=Again, 2=Hard, 3=Good, 4=Easy. Uses SM-2."""
        card = None
        for c in self.cards:
            if c.id == card_id:
                card = c
                break
        if not card:
            return

        card.review_count += 1
        card.last_reviewed = date.today().isoformat()

        # Map 1-4 rating to SM-2 quality 0-5
        quality_map = {1: 0, 2: 2, 3: 3, 4: 5}
        quality = quality_map.get(rating, 3)

        if quality < 3:
            card.interval_days = 1
        else:
            if card.review_count == 1:
                card.interval_days = 1
            elif card.review_count == 2:
                card.interval_days = 6
            else:
                card.interval_days = max(1, round(card.interval_days * card.ease_factor))

        card.ease_factor = max(
            1.3,
            card.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)),
        )
        card.next_review = (date.today() + timedelta(days=card.interval_days)).isoformat()
        self._save()

    def auto_create_from_grade(self, question: str, model_answer: str,
                                subject: str, topic: str, percentage: int) -> Optional[Flashcard]:
        """Auto-create a flashcard if score < 60%."""
        if percentage >= 60:
            return None
        # Avoid duplicates
        for c in self.cards:
            if c.front == question and c.subject == subject:
                return None
        card = Flashcard(
            id=f"fc_auto_{len(self.cards)}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            front=question,
            back=model_answer or "Review this topic",
            subject=subject,
            topic=topic,
            source="auto_grading",
        )
        self.add(card)
        return card

    def _save(self) -> None:
        data = [asdict(c) for c in self.cards]
        FLASHCARD_PATH.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        if not FLASHCARD_PATH.exists():
            return
        try:
            data = json.loads(FLASHCARD_PATH.read_text())
            for c in data:
                self.cards.append(Flashcard(**c))
        except (json.JSONDecodeError, KeyError, TypeError):
            pass


# ── Misconception Tracking ────────────────────────────────────────

MISCONCEPTION_PATTERNS = {
    "evaluation_weakness": {
        "keywords": ["one-sided", "counter-argument", "both sides", "balanced", "limitation"],
        "name": "Evaluation Weakness",
        "description": "Struggling to argue both sides of an issue",
    },
    "vocabulary_gap": {
        "keywords": ["terminology", "key terms", "technical", "subject-specific", "vocabulary"],
        "name": "Vocabulary Gap",
        "description": "Not using enough subject-specific terminology",
    },
    "lack_of_precision": {
        "keywords": ["vague", "generic", "specific", "precise", "detail"],
        "name": "Lack of Precision",
        "description": "Answers are too vague or lack specific examples",
    },
    "essay_structure": {
        "keywords": ["structure", "organization", "paragraph", "introduction", "conclusion"],
        "name": "Essay Structure Issues",
        "description": "Problems with organizing and structuring responses",
    },
    "cause_effect": {
        "keywords": ["reason", "because", "cause", "effect", "mechanism", "why"],
        "name": "Weak Causal Reasoning",
        "description": "Not explaining WHY or HOW things happen",
    },
    "data_interpretation": {
        "keywords": ["data", "graph", "trend", "pattern", "interpret"],
        "name": "Data Interpretation",
        "description": "Difficulty reading and interpreting data/graphs",
    },
}


@dataclass
class MisconceptionEntry:
    pattern_id: str
    subject: str
    count: int = 1
    first_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    trending: str = "new"  # "new" | "persisting" | "improving"


class MisconceptionLog:
    """Tracks recurring misconception patterns from grading feedback."""

    def __init__(self) -> None:
        self.entries: list[MisconceptionEntry] = []
        self._load()

    def scan_improvements(self, improvements: list[str], subject: str) -> list[str]:
        """Scan improvement feedback for misconception patterns. Returns detected pattern IDs."""
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

        if detected:
            self._save()
        return detected

    def active_misconceptions(self, subject: str = "") -> list[dict]:
        """Return active misconceptions, optionally filtered by subject."""
        entries = self.entries
        if subject:
            entries = [e for e in entries if e.subject == subject]

        result = []
        for e in entries:
            pattern_def = MISCONCEPTION_PATTERNS.get(e.pattern_id, {})
            result.append({
                "pattern_id": e.pattern_id,
                "name": pattern_def.get("name", e.pattern_id),
                "description": pattern_def.get("description", ""),
                "subject": e.subject,
                "count": e.count,
                "trending": e.trending,
                "first_seen": e.first_seen,
                "last_seen": e.last_seen,
            })
        result.sort(key=lambda x: -x["count"])
        return result

    def _record(self, pattern_id: str, subject: str) -> None:
        for e in self.entries:
            if e.pattern_id == pattern_id and e.subject == subject:
                old_count = e.count
                e.count += 1
                e.last_seen = datetime.now().isoformat()
                # Trending logic
                if e.count > old_count + 2:
                    e.trending = "persisting"
                return

        self.entries.append(MisconceptionEntry(
            pattern_id=pattern_id,
            subject=subject,
        ))

    def _save(self) -> None:
        data = [asdict(e) for e in self.entries]
        MISCONCEPTION_PATH.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        if not MISCONCEPTION_PATH.exists():
            return
        try:
            data = json.loads(MISCONCEPTION_PATH.read_text())
            for e in data:
                self.entries.append(MisconceptionEntry(**e))
        except (json.JSONDecodeError, KeyError, TypeError):
            pass


# ── Mock Exam Reports ─────────────────────────────────────────────

@dataclass
class MockExamReport:
    id: str
    subject: str
    level: str
    date: str
    total_marks_earned: int
    total_marks_possible: int
    percentage: float
    grade: int
    questions: list[dict] = field(default_factory=list)
    # Each question: {text, command_term, marks, mark_earned, percentage}
    command_term_breakdown: dict = field(default_factory=dict)
    time_taken_minutes: int = 0
    improvements: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class MockExamReportStore:
    """Stores mock exam reports for history/comparison."""

    def __init__(self) -> None:
        self.reports: list[MockExamReport] = []
        self._load()

    def add(self, report: MockExamReport) -> None:
        self.reports.append(report)
        self._save()

    def by_subject(self, subject: str) -> list[MockExamReport]:
        return [r for r in self.reports if r.subject == subject]

    def recent(self, n: int = 5) -> list[MockExamReport]:
        return list(reversed(self.reports[-n:]))

    def _save(self) -> None:
        data = [asdict(r) for r in self.reports]
        MOCK_REPORT_PATH.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        if not MOCK_REPORT_PATH.exists():
            return
        try:
            data = json.loads(MOCK_REPORT_PATH.read_text())
            for r in data:
                self.reports.append(MockExamReport(**r))
        except (json.JSONDecodeError, KeyError, TypeError):
            pass


# ── Notification System ──────────────────────────────────────

NOTIFICATION_TYPES = {
    "flashcard_due": {
        "title_template": "{count} flashcards due for review",
        "icon": "cards",
        "category": "study",
    },
    "streak_risk": {
        "title_template": "Your {streak}-day streak is at risk!",
        "icon": "fire",
        "category": "motivation",
    },
    "weekly_summary": {
        "title_template": "Weekly Progress: {questions} questions, avg Grade {avg_grade}",
        "icon": "chart",
        "category": "progress",
    },
    "plan_reminder": {
        "title_template": "Study plan: {task_count} tasks for today",
        "icon": "calendar",
        "category": "study",
    },
    "milestone_due": {
        "title_template": "{milestone} is approaching ({days} days)",
        "icon": "clock",
        "category": "lifecycle",
    },
    "achievement": {
        "title_template": "New badge earned: {badge_name}!",
        "icon": "trophy",
        "category": "motivation",
    },
}


@dataclass
class Notification:
    id: str
    type: str
    title: str
    body: str
    created_at: str
    read: bool = False
    dismissed: bool = False
    action_url: str = ""
    data: dict = field(default_factory=dict)


class NotificationStore:
    """Manages in-app notifications. Persists to JSON."""

    def __init__(self) -> None:
        self.notifications: list[Notification] = []
        self._load()

    def add(self, notif: Notification) -> None:
        self.notifications.append(notif)
        self._save()

    def unread_count(self) -> int:
        return sum(1 for n in self.notifications if not n.read and not n.dismissed)

    def recent(self, n: int = 20) -> list[Notification]:
        active = [ntf for ntf in self.notifications if not ntf.dismissed]
        return sorted(active, key=lambda ntf: ntf.created_at, reverse=True)[:n]

    def has_today(self, notif_type: str) -> bool:
        """Check if a notification of this type was already created today."""
        today = date.today().isoformat()
        return any(
            n.type == notif_type and n.created_at[:10] == today
            for n in self.notifications
        )

    def mark_read(self, notif_id: str) -> None:
        for n in self.notifications:
            if n.id == notif_id:
                n.read = True
                break
        self._save()

    def mark_all_read(self) -> None:
        for n in self.notifications:
            n.read = True
        self._save()

    def dismiss(self, notif_id: str) -> None:
        for n in self.notifications:
            if n.id == notif_id:
                n.dismissed = True
                break
        self._save()

    def _save(self) -> None:
        data = [asdict(n) for n in self.notifications[-100:]]  # Keep last 100
        NOTIFICATION_PATH.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        if not NOTIFICATION_PATH.exists():
            return
        try:
            data = json.loads(NOTIFICATION_PATH.read_text())
            for n in data:
                self.notifications.append(Notification(**n))
        except (json.JSONDecodeError, KeyError, TypeError):
            pass


# ── Collaboration: Shared Question Sets ──────────────────────


@dataclass
class SharedQuestionSet:
    id: str
    title: str
    description: str
    author: str
    subject: str
    topic: str
    level: str
    questions: list[dict] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    import_count: int = 0


class SharedQuestionStore:
    """Manages exported/imported question sets."""

    def __init__(self) -> None:
        self.sets: list[SharedQuestionSet] = []
        self._load()

    def export_set(
        self, title: str, description: str, subject: str,
        topic: str, level: str, questions: list[dict], author: str,
    ) -> SharedQuestionSet:
        qset = SharedQuestionSet(
            id=f"qs_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            title=title,
            description=description,
            author=author,
            subject=subject,
            topic=topic,
            level=level,
            questions=questions,
        )
        self.sets.append(qset)
        self._save()
        return qset

    def import_set(self, data: dict) -> SharedQuestionSet:
        qset = SharedQuestionSet(**data)
        qset.import_count += 1
        self.sets.append(qset)
        self._save()
        return qset

    def to_json(self, set_id: str) -> str:
        for qs in self.sets:
            if qs.id == set_id:
                return json.dumps(asdict(qs), indent=2)
        return ""

    def _save(self) -> None:
        data = [asdict(qs) for qs in self.sets]
        SHARED_QUESTIONS_PATH.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        if not SHARED_QUESTIONS_PATH.exists():
            return
        try:
            data = json.loads(SHARED_QUESTIONS_PATH.read_text())
            for qs in data:
                self.sets.append(SharedQuestionSet(**qs))
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
