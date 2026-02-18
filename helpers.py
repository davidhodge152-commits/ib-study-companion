"""
Shared helpers used across blueprints.

Extracted from app.py to break circular dependencies.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import datetime, date, timedelta
from functools import wraps
from pathlib import Path
from typing import Any

from flask import abort, redirect, request, url_for
from flask_login import current_user

from auth import login_manager

DATA_DIR = Path(__file__).parent / "data"
if not os.environ.get("VERCEL"):
    DATA_DIR.mkdir(exist_ok=True)


def current_user_id() -> int:
    """Return the current authenticated user's ID, or 1 as fallback."""
    if current_user.is_authenticated:
        return current_user.id
    return 1


def login_or_guest(f: Callable) -> Callable:
    """Allow both authenticated users and guest sessions."""
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        from flask import session as flask_session
        if current_user.is_authenticated or flask_session.get("guest"):
            return f(*args, **kwargs)
        return login_manager.unauthorized()
    return decorated


def teacher_required(f: Callable) -> Callable:
    """Decorator that requires user to have teacher or admin role."""
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if getattr(current_user, "role", "student") not in ("teacher", "admin"):
            abort(403)
        return f(*args, **kwargs)
    return decorated


COMMAND_TERM_THRESHOLDS = {
    "Define": 85, "State": 85, "List": 85, "Identify": 80,
    "Describe": 70, "Outline": 70, "Distinguish": 70,
    "Explain": 65, "Suggest": 65, "Annotate": 70,
    "Analyse": 60, "Compare": 60, "Compare and contrast": 60, "Contrast": 60,
    "Evaluate": 55, "Discuss": 55, "To what extent": 55, "Justify": 55, "Examine": 55,
}


def generate_recommendation(profile: Any, grade_log: Any) -> dict[str, str]:
    """Deterministic recommendation: biggest gap -> weakest command term -> action."""
    from db_stores import TopicProgressStoreDB
    from subject_config import get_syllabus_topics

    gaps = profile.compute_gaps(grade_log)
    ct_stats = grade_log.command_term_stats()

    target_subject = None
    for g in gaps:
        if g["status"] in ("behind", "close"):
            target_subject = g
            break

    if not target_subject:
        for g in gaps:
            if g["status"] == "no_data":
                target_subject = g
                break
        if not target_subject and gaps:
            target_subject = gaps[0]

    if not target_subject:
        return {
            "subject": "",
            "reason": "Add subjects to your profile to get recommendations.",
            "command_term_focus": "",
            "priority": "low",
        }

    weakest_ct = ""
    weakest_ct_pct = 100
    for ct, stats in ct_stats.items():
        if stats["count"] >= 1 and stats["avg_percentage"] < weakest_ct_pct:
            weakest_ct = ct
            weakest_ct_pct = stats["avg_percentage"]

    if target_subject["status"] == "no_data":
        reason = f"Start practicing {target_subject['subject']} — no data yet."
        priority = "medium"
    elif target_subject["status"] == "behind":
        reason = (
            f"{target_subject['subject']} {target_subject['level']} is your biggest gap "
            f"({target_subject['gap']:+d} grade{'s' if abs(target_subject['gap']) != 1 else ''} "
            f"from target {target_subject['target']})."
        )
        priority = "high"
    else:
        reason = (
            f"{target_subject['subject']} {target_subject['level']} is close to target "
            f"({target_subject['gap']:+d})."
        )
        priority = "medium"

    # Enrich with syllabus coverage data
    tp_store = TopicProgressStoreDB(current_user_id())
    topics = get_syllabus_topics(target_subject["subject"])
    if topics:
        tp = tp_store.get(target_subject["subject"])
        coverage = tp.overall_coverage(topics)
        if coverage < 100:
            for t in topics:
                if not tp.topics.get(t.id):
                    reason += f" You've covered {coverage:.0f}% of the syllabus — try {t.name} next."
                    break

    ct_detail = ""
    if weakest_ct and weakest_ct_pct < 70:
        ct_detail = f" Your weakest command term is {weakest_ct} ({weakest_ct_pct:.0f}% avg)."
        reason += ct_detail

    return {
        "subject": target_subject["subject"],
        "level": target_subject["level"],
        "reason": reason,
        "command_term_focus": weakest_ct if weakest_ct_pct < 70 else "",
        "priority": priority,
    }


def _command_term_alignment(command_term: str, improvements: list[str]) -> str:
    if not command_term or not improvements:
        return ""

    ct_lower = command_term.lower()
    checks = {
        "evaluate": ["one-sided", "counter-argument", "both sides", "balanced", "limitation"],
        "discuss": ["one-sided", "counter-argument", "both sides", "balanced"],
        "analyse": ["break down", "component", "relationship", "cause"],
        "explain": ["reason", "mechanism", "cause", "why"],
        "compare": ["similarit", "difference", "contrast", "both"],
        "define": ["definition", "precise", "terminology"],
    }

    keywords = checks.get(ct_lower, [])
    if not keywords:
        return ""

    feedback_text = " ".join(improvements).lower()
    for kw in keywords:
        if kw in feedback_text:
            return f"The examiner noted issues related to '{command_term}' expectations — make sure you understand what this command term requires."

    return ""


def _generate_text_insights(
    grade_log,
    profile,
    ct_stats: dict,
    gaps: list[dict],
) -> list[dict]:
    insights = []

    for g in gaps:
        if g["status"] == "behind":
            insights.append({
                "severity": "red",
                "title": f"{g['subject']} {g['level']} needs attention",
                "body": f"You're predicted a {g['predicted']}, but your target is {g['target']} ({g['gap']:+d} gap).",
                "action": f"Focus your next study sessions on {g['subject']}.",
            })
            break

    weakest_ct = None
    for ct, stats in sorted(ct_stats.items(), key=lambda x: x[1]["avg_percentage"]):
        if stats["count"] >= 2 and stats["avg_percentage"] < 65:
            weakest_ct = (ct, stats)
            break

    if weakest_ct:
        ct_name, ct_data = weakest_ct
        insights.append({
            "severity": "yellow",
            "title": f"Weak on '{ct_name}' questions",
            "body": f"Average {ct_data['avg_percentage']}% across {ct_data['count']} attempts.",
            "action": f"Use Command Term Trainer to practice '{ct_name}' questions.",
        })

    entries = grade_log.entries
    if len(entries) >= 4:
        recent = entries[-4:]
        older = entries[-8:-4] if len(entries) >= 8 else entries[:4]
        recent_avg = sum(e.percentage for e in recent) / len(recent)
        older_avg = sum(e.percentage for e in older) / len(older)
        diff = recent_avg - older_avg

        if diff > 5:
            insights.append({
                "severity": "green",
                "title": "Performance is improving",
                "body": f"Your recent average is {recent_avg:.0f}%, up from {older_avg:.0f}% (+{diff:.0f}%).",
                "action": "Keep up the momentum!",
            })
        elif diff < -5:
            insights.append({
                "severity": "red",
                "title": "Performance is declining",
                "body": f"Your recent average is {recent_avg:.0f}%, down from {older_avg:.0f}% ({diff:.0f}%).",
                "action": "Consider reviewing fundamentals before attempting harder questions.",
            })

    if len(insights) < 3 and len(entries) > 0:
        total = len(entries)
        avg_pct = sum(e.percentage for e in entries) / total
        insights.append({
            "severity": "blue",
            "title": f"{total} answers graded so far",
            "body": f"Overall average: {avg_pct:.0f}%.",
            "action": "Keep practicing to build a clearer picture of your strengths.",
        })

    return insights[:3]


def _analyze_writing_style(text: str) -> None:
    from extensions import EngineManager
    from db_stores import WritingProfileDB

    engine = EngineManager.get_engine()
    prompt = f"""Analyze this student's writing from an IB exam. Identify:

1. VERBOSITY: Are they concise or verbose? Do they tend to over-explain or under-explain?
2. TERMINOLOGY: How well do they use subject-specific terminology? Do they define terms?
3. ARGUMENT_STRUCTURE: How do they organize arguments? Do they use clear topic sentences? Do they provide balanced evaluations?
4. PATTERNS: List 3-5 recurring patterns (good or bad) in their writing.
5. SUMMARY: A 2-3 sentence overall profile of this student's exam writing style.

Format your response EXACTLY as:
VERBOSITY: [description]
TERMINOLOGY: [description]
ARGUMENT_STRUCTURE: [description]
PATTERNS:
- [pattern 1]
- [pattern 2]
- [pattern 3]
SUMMARY: [2-3 sentences]

Student's exam text:
{text[:8000]}"""

    raw = engine.ask(prompt)

    uid = current_user_id()
    wp_db = WritingProfileDB(uid)
    existing = wp_db.load()

    verbosity = ""
    terminology_usage = ""
    argument_structure = ""
    summary = ""
    common_patterns = []
    analyzed_count = (existing["analyzed_count"] if existing else 0)

    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("VERBOSITY:"):
            verbosity = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("TERMINOLOGY:"):
            terminology_usage = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("ARGUMENT_STRUCTURE:"):
            argument_structure = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("SUMMARY:"):
            summary = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("- ") and verbosity:
            common_patterns.append(stripped[2:])

    analyzed_count += 1
    wp_db.save(
        verbosity=verbosity,
        terminology_usage=terminology_usage,
        argument_structure=argument_structure,
        common_patterns=common_patterns,
        summary=summary,
        analyzed_count=analyzed_count,
        last_updated=datetime.now().isoformat(),
    )


def _last_active_date(activity_log) -> date:
    if not activity_log.entries:
        return date.today() - timedelta(days=30)
    dates = [e.date for e in activity_log.entries]
    return date.fromisoformat(max(dates))


def generate_pending_notifications(user_id: int) -> list[Any]:
    """Check all notification triggers and create new notifications if needed."""
    from profile import Notification
    from db_stores import (
        NotificationStoreDB, FlashcardDeckDB, ActivityLogDB,
        GamificationProfileDB, StudyPlanDB,
    )

    store = NotificationStoreDB(user_id)
    new_notifications = []
    today = date.today().isoformat()

    # 1. Flashcards due
    fc_deck = FlashcardDeckDB(user_id)
    due_count = fc_deck.due_count()
    if due_count > 0 and not store.has_today("flashcard_due"):
        notif = Notification(
            id=f"fc_due_{today}",
            type="flashcard_due",
            title=f"{due_count} flashcards due for review",
            body=f"You have {due_count} flashcards waiting. Review them to strengthen your memory.",
            created_at=datetime.now().isoformat(),
            action_url="/flashcards",
            data={"count": due_count},
        )
        store.add(notif)
        new_notifications.append(notif)

    # 2. Streak at risk
    activity_log = ActivityLogDB(user_id)
    gam = GamificationProfileDB(user_id)
    if gam.current_streak > 0:
        active_dates = {e.date for e in activity_log.entries}
        if today not in active_dates and not store.has_today("streak_risk"):
            notif = Notification(
                id=f"streak_risk_{today}",
                type="streak_risk",
                title=f"Your {gam.current_streak}-day streak is at risk!",
                body="Study today to keep your streak alive.",
                created_at=datetime.now().isoformat(),
                action_url="/study",
                data={"streak": gam.current_streak},
            )
            store.add(notif)
            new_notifications.append(notif)

    # 3. Study plan tasks
    plan_data = StudyPlanDB(user_id).load()
    if plan_data:
        for dp in plan_data["daily_plans"]:
            if dp.date == today:
                incomplete = sum(1 for t in dp.tasks if not t.completed)
                if incomplete > 0 and not store.has_today("plan_reminder"):
                    notif = Notification(
                        id=f"plan_{today}",
                        type="plan_reminder",
                        title=f"{incomplete} study tasks for today",
                        body=f"Your study plan has {incomplete} uncompleted tasks.",
                        created_at=datetime.now().isoformat(),
                        action_url="/planner",
                        data={"task_count": incomplete},
                    )
                    store.add(notif)
                    new_notifications.append(notif)
                break

    return new_notifications


# ── Pagination ──────────────────────────────────────────────

def paginate_args(default_limit: int = 20, max_limit: int = 100) -> tuple[int, int]:
    """Extract page/limit from request.args. Returns (page, limit)."""
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1
    try:
        limit = min(max_limit, max(1, int(request.args.get("limit", default_limit))))
    except (ValueError, TypeError):
        limit = default_limit
    return page, limit


def paginated_response(items: list, total: int, page: int, limit: int) -> dict:
    """Standard pagination envelope."""
    return {
        "items": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": max(1, (total + limit - 1) // limit),
        },
    }
