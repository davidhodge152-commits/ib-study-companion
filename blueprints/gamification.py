"""Gamification, misconception, and mock report routes."""

from __future__ import annotations

from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_login import login_required

from helpers import current_user_id
from profile import BADGE_DEFINITIONS, MockExamReport
from db_stores import (
    ActivityLogDB,
    GamificationProfileDB,
    MisconceptionLogDB,
    MockExamReportStoreDB,
)
from subject_config import get_subject_config

bp = Blueprint("gamification", __name__)


@bp.route("/api/gamification")
@login_required
def api_gamification():
    uid = current_user_id()
    gam = GamificationProfileDB(uid)
    activity_log = ActivityLogDB(uid)
    gam.update_streak(activity_log)
    return jsonify({
        "total_xp": gam.total_xp,
        "level": gam.level,
        "xp_progress_pct": gam.xp_progress_pct,
        "xp_for_next_level": gam.xp_for_next_level,
        "current_streak": gam.current_streak,
        "longest_streak": gam.longest_streak,
        "daily_xp_today": gam.daily_xp_today,
        "daily_goal_xp": gam.daily_goal_xp,
        "daily_goal_pct": gam.daily_goal_pct,
        "badges": [
            {**BADGE_DEFINITIONS.get(b, {"name": b}), "id": b}
            for b in gam.badges
        ],
        "streak_freeze_available": gam.streak_freeze_available,
        "total_questions_answered": gam.total_questions_answered,
    })


@bp.route("/api/misconceptions")
@login_required
def api_misconceptions():
    uid = current_user_id()
    misc_log = MisconceptionLogDB(uid)
    subject = request.args.get("subject", "")
    return jsonify({
        "misconceptions": misc_log.active_misconceptions(subject),
    })


@bp.route("/api/mock-reports")
@login_required
def api_mock_reports():
    uid = current_user_id()
    store = MockExamReportStoreDB(uid)
    subject = request.args.get("subject", "")
    if subject:
        reports = store.by_subject(subject)
    else:
        reports = store.recent(10)
    return jsonify({
        "reports": [
            {
                "id": r.id,
                "subject": r.subject,
                "level": r.level,
                "date": r.date,
                "percentage": r.percentage,
                "grade": r.grade,
                "total_marks_earned": r.total_marks_earned,
                "total_marks_possible": r.total_marks_possible,
                "command_term_breakdown": r.command_term_breakdown,
                "improvements": r.improvements,
                "created_at": r.created_at,
            }
            for r in reports
        ],
    })


@bp.route("/api/mock-reports/create", methods=["POST"])
@login_required
def api_mock_report_create():
    """Create a mock exam report from completed exam sim session results."""
    data = request.get_json()
    subject = data.get("subject", "")
    level = data.get("level", "HL")
    results = data.get("results", [])

    if not subject or not results:
        return jsonify({"error": "Subject and results are required"}), 400

    total_earned = sum(r.get("mark_earned", 0) for r in results)
    total_possible = sum(r.get("marks", 0) for r in results)
    overall_pct = round(total_earned / total_possible * 100) if total_possible > 0 else 0

    config = get_subject_config(subject)
    boundaries = {}
    if config:
        boundaries = config.grade_boundaries_hl if level == "HL" else config.grade_boundaries_sl
    grade = 1
    for g in sorted(boundaries.keys(), reverse=True):
        if overall_pct >= boundaries[g]:
            grade = g
            break

    ct_breakdown = {}
    for r in results:
        ct = r.get("command_term", "Unknown")
        if ct not in ct_breakdown:
            ct_breakdown[ct] = {"total": 0, "earned": 0, "count": 0}
        ct_breakdown[ct]["total"] += r.get("marks", 0)
        ct_breakdown[ct]["earned"] += r.get("mark_earned", 0)
        ct_breakdown[ct]["count"] += 1

    all_improvements = []
    for r in results:
        all_improvements.extend(r.get("improvements", []))

    improvements_text = []
    if all_improvements:
        seen = set()
        for imp in all_improvements:
            key = imp.lower().strip()[:50]
            if key not in seen:
                seen.add(key)
                improvements_text.append(imp)
            if len(improvements_text) >= 5:
                break

    report = MockExamReport(
        id=datetime.now().strftime("%Y%m%d_%H%M%S"),
        subject=subject,
        level=level,
        date=datetime.now().strftime("%Y-%m-%d"),
        percentage=overall_pct,
        grade=grade,
        total_marks_earned=total_earned,
        total_marks_possible=total_possible,
        command_term_breakdown=ct_breakdown,
        improvements=improvements_text[:5],
        created_at=datetime.now().isoformat(),
    )

    uid = current_user_id()
    store = MockExamReportStoreDB(uid)
    store.add(report)

    gam = GamificationProfileDB(uid)
    gam.check_badges(questions_answered=0, subjects=set(), mock_complete=True)
    gam.save()

    return jsonify({
        "success": True,
        "report": {
            "id": report.id,
            "grade": report.grade,
            "percentage": report.percentage,
            "total_marks_earned": report.total_marks_earned,
            "total_marks_possible": report.total_marks_possible,
            "command_term_breakdown": report.command_term_breakdown,
            "improvements": report.improvements,
        }
    })
