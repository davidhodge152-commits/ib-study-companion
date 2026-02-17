"""Executive Function Agent — Study planning and burnout detection.

Optimizes study time using Bayesian knowledge data + deadline awareness.
Generates smart study plans, daily briefings, detects burnout signals,
and dynamically reprioritizes when deadlines change.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, date, timedelta
from typing import TYPE_CHECKING

from dotenv import load_dotenv

from agents.base import AgentResponse

if TYPE_CHECKING:
    from rag_engine import RAGEngine

load_dotenv()

BRIEFING_SYSTEM = """You are a supportive IB study coach giving a daily briefing.

STUDENT: {name}
TODAY: {today}
EXAM SESSION: {exam_session}
DAYS UNTIL EXAMS: {days_until_exams}

SUBJECT MASTERY:
{mastery_summary}

UPCOMING DEADLINES:
{deadlines}

RECENT ACTIVITY:
{activity_summary}

BURNOUT SIGNALS: {burnout_status}

Provide a brief, motivating daily briefing (3-5 sentences) that:
1. Greets the student by name
2. Highlights the most urgent priority
3. Celebrates recent progress (streaks, improvements)
4. If burnout risk is elevated, suggest a lighter study day
5. Recommends specific subjects/topics to focus on today

Keep the tone warm, encouraging, and action-oriented."""

PLAN_PROMPT = """Create an optimized study plan for the next {days} days.

STUDENT CONTEXT:
{context}

MASTERY DATA:
{mastery_data}

DEADLINES:
{deadlines}

SPACED REPETITION DUE:
{review_due}

CONSTRAINTS:
- Target {daily_minutes} minutes of study per day
- Variety: don't schedule same subject >2 consecutive blocks
- Spaced repetition reviews take priority
- Weight low-mastery + imminent-deadline topics highest
- Include short breaks every 45-60 minutes

FORMAT each day as:
DAY: [date]
BLOCK 1: [time] [subject] - [specific topic/task] ([minutes]min)
BLOCK 2: [time] [subject] - [specific topic/task] ([minutes]min)
...
TOTAL: [total minutes]

PRIORITY_SUBJECTS: [ordered list of subjects to focus on]
RATIONALE: [brief explanation of why this allocation]"""


class ExecutiveAgent:
    """Study planning and executive function support agent."""

    AGENT_NAME = "executive_agent"

    def __init__(self, rag_engine: RAGEngine | None = None) -> None:
        self.rag_engine = rag_engine
        self._claude_client = None
        self._gemini_model = None
        self._provider = "none"
        self._init_provider()

    def _init_provider(self) -> None:
        """Initialize best available LLM provider."""
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            try:
                import anthropic

                self._claude_client = anthropic.Anthropic(api_key=anthropic_key)
                self._provider = "claude"
                return
            except ImportError:
                pass

        google_key = os.getenv("GOOGLE_API_KEY")
        if google_key:
            try:
                import google.generativeai as genai

                genai.configure(api_key=google_key)
                self._gemini_model = genai.GenerativeModel("gemini-2.0-flash")
                self._provider = "gemini"
            except ImportError:
                pass

    def daily_briefing(self, user_id: int) -> AgentResponse:
        """Generate a personalized daily study briefing."""
        if self._provider == "none":
            return AgentResponse(
                content="Executive agent requires an API key (Anthropic or Google).",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

        # Gather student context
        ctx = self._gather_context(user_id)
        burnout = self.detect_burnout(user_id)

        system = BRIEFING_SYSTEM.format(
            name=ctx.get("name", "Student"),
            today=date.today().isoformat(),
            exam_session=ctx.get("exam_session", ""),
            days_until_exams=ctx.get("days_until_exams", "?"),
            mastery_summary=ctx.get("mastery_summary", "No data yet"),
            deadlines=ctx.get("deadlines_text", "No deadlines set"),
            activity_summary=ctx.get("activity_summary", "No recent activity"),
            burnout_status=burnout.get("risk_level", "low"),
        )

        try:
            response_text = self._call_llm(
                "Generate today's study briefing.", system
            )

            return AgentResponse(
                content=response_text,
                agent=self.AGENT_NAME,
                confidence=0.85,
                metadata={
                    "burnout_risk": burnout.get("risk_level", "low"),
                    "burnout_signals": burnout.get("signals", []),
                    "priority_subjects": ctx.get("priority_subjects", []),
                },
                follow_up="Would you like me to generate a detailed study plan for this week?",
            )
        except Exception as e:
            return AgentResponse(
                content=f"Error generating briefing: {e}",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

    def generate_smart_plan(
        self,
        user_id: int,
        days_ahead: int = 7,
        daily_minutes: int = 180,
    ) -> AgentResponse:
        """Generate an optimized study plan using mastery + deadline data."""
        if self._provider == "none":
            return AgentResponse(
                content="Executive agent requires an API key.",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

        ctx = self._gather_context(user_id)
        mastery_data = self._get_mastery_data(user_id, ctx.get("subjects", []))
        review_due = self._get_review_due(user_id)
        deadlines = self._get_deadlines(user_id)

        prompt = PLAN_PROMPT.format(
            days=days_ahead,
            context=json.dumps({
                "name": ctx.get("name", "Student"),
                "subjects": ctx.get("subjects", []),
                "exam_session": ctx.get("exam_session", ""),
            }),
            mastery_data=json.dumps(mastery_data, indent=2),
            deadlines=json.dumps(deadlines, indent=2),
            review_due=json.dumps(review_due, indent=2),
            daily_minutes=daily_minutes,
        )

        try:
            response_text = self._call_llm(prompt)

            # Save the plan
            self._save_plan(user_id, days_ahead, response_text, mastery_data)

            return AgentResponse(
                content=response_text,
                agent=self.AGENT_NAME,
                confidence=0.85,
                metadata={
                    "days_ahead": days_ahead,
                    "daily_minutes": daily_minutes,
                    "mastery_data": mastery_data,
                    "deadlines": deadlines,
                },
                follow_up="Would you like me to adjust the plan or add specific deadlines?",
            )
        except Exception as e:
            return AgentResponse(
                content=f"Error generating study plan: {e}",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

    def detect_burnout(self, user_id: int) -> dict:
        """Analyze recent activity patterns for burnout signals."""
        signals = []
        risk_level = "low"

        try:
            from db_stores import ActivityLogDB, GamificationProfileDB

            activity = ActivityLogDB(user_id)
            entries = activity.entries[-14:]  # Last 2 weeks

            if not entries:
                return {"risk_level": "low", "signals": [], "recommendation": ""}

            # Check for declining session duration
            if len(entries) >= 4:
                recent = entries[-4:]
                older = entries[-8:-4] if len(entries) >= 8 else entries[:4]

                recent_duration = sum(e.duration_minutes for e in recent) / len(recent) if recent else 0
                older_duration = sum(e.duration_minutes for e in older) / len(older) if older else 0

                if older_duration > 0 and recent_duration < older_duration * 0.6:
                    signals.append("declining_session_duration")

                # Check for declining accuracy
                recent_pct = sum(e.avg_percentage for e in recent) / len(recent) if recent else 0
                older_pct = sum(e.avg_percentage for e in older) / len(older) if older else 0

                if older_pct > 0 and recent_pct < older_pct - 10:
                    signals.append("declining_accuracy")

            # Check for skipped days
            if len(entries) >= 3:
                dates = sorted(set(e.date for e in entries))
                if len(dates) >= 2:
                    total_days = (date.fromisoformat(dates[-1]) - date.fromisoformat(dates[0])).days + 1
                    active_days = len(dates)
                    if total_days > 0 and active_days / total_days < 0.4:
                        signals.append("frequent_skipped_days")

            # Check for excessive hours
            recent_week = [e for e in entries if e.date >= (date.today() - timedelta(days=7)).isoformat()]
            total_minutes = sum(e.duration_minutes for e in recent_week)
            if total_minutes > 25 * 60:  # >25 hours in a week
                signals.append("excessive_study_hours")

            # Determine risk level
            if len(signals) >= 3:
                risk_level = "high"
            elif len(signals) >= 1:
                risk_level = "medium"

        except Exception:
            pass

        recommendations = {
            "low": "You're maintaining a healthy study rhythm. Keep it up!",
            "medium": "Consider mixing in lighter review sessions to avoid fatigue.",
            "high": "Take a proper break today. You'll retain more with rest. Consider a walk or activity you enjoy.",
        }

        return {
            "risk_level": risk_level,
            "signals": signals,
            "recommendation": recommendations.get(risk_level, ""),
        }

    def reprioritize(
        self, user_id: int, event: str
    ) -> AgentResponse:
        """Recalculate study plan based on changed circumstances."""
        if self._provider == "none":
            return AgentResponse(
                content="Executive agent requires an API key.",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

        ctx = self._gather_context(user_id)
        mastery_data = self._get_mastery_data(user_id, ctx.get("subjects", []))

        prompt = (
            f"The student reports a change: '{event}'\n\n"
            f"Current study context:\n{json.dumps(ctx, indent=2)}\n\n"
            f"Current mastery:\n{json.dumps(mastery_data, indent=2)}\n\n"
            "Recalculate priorities and suggest how to adjust the study plan. "
            "Be specific about what to add, remove, or reschedule."
        )

        try:
            response_text = self._call_llm(prompt)
            return AgentResponse(
                content=response_text,
                agent=self.AGENT_NAME,
                confidence=0.8,
                metadata={"event": event},
                follow_up="Would you like me to generate a complete updated plan?",
            )
        except Exception as e:
            return AgentResponse(
                content=f"Error reprioritizing: {e}",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

    def _gather_context(self, user_id: int) -> dict:
        """Gather full student context for planning."""
        ctx: dict = {"user_id": user_id, "name": "Student", "subjects": []}

        try:
            from db_stores import StudentProfileDB, GamificationProfileDB, ActivityLogDB

            profile = StudentProfileDB(user_id)
            ctx["name"] = profile.name
            ctx["exam_session"] = profile.exam_session
            ctx["subjects"] = [
                {"name": s.name, "level": s.level, "target": s.target_grade}
                for s in profile.subjects
            ]

            # Days until exams (estimate from exam_session)
            exam_session = profile.exam_session or ""
            if "May" in exam_session:
                year = exam_session.split()[-1] if len(exam_session.split()) > 1 else str(date.today().year)
                try:
                    exam_date = date(int(year), 5, 1)
                    ctx["days_until_exams"] = max(0, (exam_date - date.today()).days)
                except ValueError:
                    ctx["days_until_exams"] = "?"
            elif "November" in exam_session:
                year = exam_session.split()[-1] if len(exam_session.split()) > 1 else str(date.today().year)
                try:
                    exam_date = date(int(year), 11, 1)
                    ctx["days_until_exams"] = max(0, (exam_date - date.today()).days)
                except ValueError:
                    ctx["days_until_exams"] = "?"

            # Gamification
            gam = GamificationProfileDB(user_id)
            ctx["streak"] = gam.current_streak

            # Recent activity
            activity = ActivityLogDB(user_id)
            recent = activity.entries[-7:]
            if recent:
                subjects_practiced = set()
                total_minutes = 0
                total_questions = 0
                for e in recent:
                    subjects_practiced.add(e.subject)
                    total_minutes += e.duration_minutes
                    total_questions += e.questions_attempted
                ctx["activity_summary"] = (
                    f"Last 7 days: {total_questions} questions across "
                    f"{len(subjects_practiced)} subjects, {total_minutes} minutes total"
                )
            else:
                ctx["activity_summary"] = "No recent activity"

        except Exception:
            pass

        # Mastery summary
        mastery_data = self._get_mastery_data(user_id, ctx.get("subjects", []))
        mastery_parts = []
        for subj, topics in mastery_data.items():
            if isinstance(topics, dict):
                states = [t.get("mastery_state", "unknown") for t in topics.values()]
                mastered = states.count("mastered")
                total = len(states)
                mastery_parts.append(
                    f"- {subj}: {mastered}/{total} topics mastered"
                )
        ctx["mastery_summary"] = "\n".join(mastery_parts) if mastery_parts else "No mastery data"

        # Priority subjects (lowest mastery first)
        priority = sorted(
            mastery_data.keys(),
            key=lambda s: sum(
                1 for t in mastery_data[s].values()
                if isinstance(t, dict) and t.get("mastery_state") == "mastered"
            ) if isinstance(mastery_data.get(s), dict) else 0,
        )
        ctx["priority_subjects"] = priority[:3]

        # Deadlines
        deadlines = self._get_deadlines(user_id)
        if deadlines:
            ctx["deadlines_text"] = "\n".join(
                f"- {d['title']} ({d['subject']}): {d['due_date']}"
                for d in deadlines[:5]
            )
        else:
            ctx["deadlines_text"] = "No deadlines set"

        return ctx

    def _get_mastery_data(
        self, user_id: int, subjects: list[dict]
    ) -> dict:
        """Get mastery map for all student subjects."""
        mastery: dict = {}
        for s in subjects:
            name = s.get("name", "")
            try:
                from knowledge_graph import SyllabusGraph
                graph = SyllabusGraph(name)
                mastery[name] = graph.get_mastery_map(user_id)
            except Exception:
                mastery[name] = {}
        return mastery

    def _get_review_due(self, user_id: int) -> list[dict]:
        """Get spaced repetition items due for review."""
        try:
            from db_stores import ReviewScheduleDB
            schedule = ReviewScheduleDB(user_id)
            due = schedule.due_today()
            return [
                {"subject": r.subject, "topic": r.topic, "command_term": r.command_term}
                for r in due[:10]
            ]
        except Exception:
            return []

    def _get_deadlines(self, user_id: int) -> list[dict]:
        """Get upcoming deadlines from the database."""
        try:
            from database import get_db
            db = get_db()
            rows = db.execute(
                "SELECT title, subject, deadline_type, due_date, importance "
                "FROM study_deadlines "
                "WHERE user_id = ? AND completed = 0 AND due_date >= ? "
                "ORDER BY due_date ASC LIMIT 10",
                (user_id, date.today().isoformat()),
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def _save_plan(
        self,
        user_id: int,
        days_ahead: int,
        plan_text: str,
        mastery_data: dict,
    ) -> None:
        """Save generated study plan to database."""
        try:
            from database import get_db

            db = get_db()

            # Identify priority subjects
            priority = sorted(
                mastery_data.keys(),
                key=lambda s: sum(
                    1 for t in mastery_data[s].values()
                    if isinstance(t, dict) and t.get("mastery_state") == "mastered"
                ) if isinstance(mastery_data.get(s), dict) else 0,
            )

            db.execute(
                "INSERT INTO smart_study_plans "
                "(user_id, generated_at, days_ahead, daily_allocations, "
                "priority_subjects) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    user_id,
                    datetime.now().isoformat(),
                    days_ahead,
                    json.dumps([plan_text]),
                    json.dumps(priority[:5]),
                ),
            )
            db.commit()
        except Exception:
            pass

    def _call_llm(self, prompt: str, system: str = "") -> str:
        """Call the configured LLM provider with resilience."""
        from ai_resilience import resilient_llm_call

        model = "claude-sonnet-4-5-20250929" if self._provider == "claude" else "gemini-2.0-flash"
        text, _ = resilient_llm_call(self._provider, model, prompt, system=system)
        return text
