"""Core routes — dashboard, onboarding, index, service_worker, redirects, health checks."""

from __future__ import annotations

import time
from datetime import date

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, send_from_directory, url_for
from flask_login import login_required

from helpers import current_user_id, generate_recommendation
from profile import IB_SUBJECTS, SubjectEntry
from db_stores import (
    ActivityLogDB,
    FlashcardDeckDB,
    GamificationProfileDB,
    GradeDetailLogDB,
    IBLifecycleDB,
    ReviewScheduleDB,
    StudentProfileDB,
    StudyPlanDB,
    TopicProgressStoreDB,
)
from subject_config import get_syllabus_topics

bp = Blueprint("core", __name__)


@bp.route("/")
@login_required
def index():
    if not StudentProfileDB.exists(current_user_id()):
        return redirect(url_for("core.onboarding"))
    return redirect(url_for("core.dashboard"))


@bp.route("/onboarding")
@login_required
def onboarding():
    profile = StudentProfileDB.load(current_user_id())
    return render_template("onboarding.html", ib_subjects=IB_SUBJECTS, profile=profile)


@bp.route("/onboarding", methods=["POST"])
@login_required
def onboarding_submit():
    name = request.form.get("name", "").strip()
    exam_session = request.form.get("exam_session", "").strip()
    target_total_points = int(request.form.get("target_total_points", 35))
    target_total_points = max(24, min(45, target_total_points))

    subjects = []
    i = 0
    while True:
        subj_name = request.form.get(f"subject_{i}")
        subj_level = request.form.get(f"level_{i}")
        if subj_name is None:
            break
        if subj_name.strip():
            target_grade = int(request.form.get(f"target_{i}", 5))
            target_grade = max(1, min(7, target_grade))
            subjects.append(SubjectEntry(
                name=subj_name.strip(),
                level=subj_level or "HL",
                target_grade=target_grade,
            ))
        i += 1

    if not name or not subjects:
        return render_template(
            "onboarding.html",
            ib_subjects=IB_SUBJECTS,
            profile=None,
            error="Please enter your name and select at least one subject.",
        )

    uid = current_user_id()
    existing = StudentProfileDB.load(uid)
    if existing:
        existing.save_fields(
            name=name,
            subjects=subjects,
            exam_session=exam_session,
            target_total_points=target_total_points,
        )
    else:
        StudentProfileDB.create(
            name=name,
            subjects=subjects,
            exam_session=exam_session,
            target_total_points=target_total_points,
        )

    lifecycle = IBLifecycleDB(uid)
    lifecycle.init_from_profile([s.name for s in subjects])

    return redirect(url_for("core.dashboard"))


@bp.route("/dashboard")
@login_required
def dashboard():
    uid = current_user_id()
    profile = StudentProfileDB.load(uid)
    if not profile:
        return redirect(url_for("core.onboarding"))

    grade_log = GradeDetailLogDB(uid)
    countdown = profile.exam_countdown()
    gaps = profile.compute_gaps(grade_log)
    predicted_total = profile.compute_predicted_total(grade_log)
    recommendation = generate_recommendation(profile, grade_log)

    recent = []
    for e in grade_log.recent(5):
        recent.append({
            "subject": e.subject_display,
            "command_term": e.command_term,
            "grade": e.grade,
            "percentage": e.percentage,
            "mark": f"{e.mark_earned}/{e.mark_total}",
            "timestamp": e.timestamp,
        })

    tp_store = TopicProgressStoreDB(uid)
    coverage_data = {}
    for s in profile.subjects:
        topics = get_syllabus_topics(s.name)
        if topics:
            tp = tp_store.get(s.name)
            coverage_data[s.name] = tp.overall_coverage(topics)

    review_sched = ReviewScheduleDB(uid)
    review_due = len(review_sched.due_today())

    lifecycle = IBLifecycleDB(uid)
    lifecycle_summary = lifecycle.summary()

    gam = GamificationProfileDB(uid)
    activity_log = ActivityLogDB(uid)
    gam.update_streak(activity_log)

    heatmap = activity_log.daily_heatmap(90)

    fc_deck = FlashcardDeckDB(uid)
    flashcard_due = fc_deck.due_count()

    plan_data = StudyPlanDB(uid).load()
    today_tasks = []
    if plan_data:
        today_str = date.today().isoformat()
        for dp in plan_data["daily_plans"]:
            if dp.date == today_str:
                for i, t in enumerate(dp.tasks):
                    today_tasks.append({
                        "subject": t.subject,
                        "topic": t.topic,
                        "task_type": t.task_type,
                        "duration_minutes": t.duration_minutes,
                        "priority": t.priority,
                        "completed": t.completed,
                        "index": i,
                        "date": dp.date,
                    })

    subject_predictions = []
    for s in profile.subjects:
        entries = grade_log.by_subject(s.name)
        if len(entries) >= 3:
            grades = [e.grade for e in entries]
            recent_grades = grades[-10:]
            mean_grade = sum(recent_grades) / len(recent_grades)
            variance = sum((g - mean_grade) ** 2 for g in recent_grades) / len(recent_grades)
            std_dev = variance ** 0.5
            confidence = "high" if len(entries) >= 15 and std_dev < 1 else "medium" if len(entries) >= 8 else "low"
            low = max(1, round(mean_grade - std_dev))
            high = min(7, round(mean_grade + std_dev))
            predicted = round(mean_grade)

            if len(grades) >= 6:
                first_half = sum(grades[:len(grades)//2]) / (len(grades)//2)
                second_half = sum(grades[len(grades)//2:]) / (len(grades) - len(grades)//2)
                if second_half - first_half > 0.5:
                    trend = "improving"
                elif first_half - second_half > 0.5:
                    trend = "declining"
                else:
                    trend = "stable"
            else:
                trend = "stable"
        elif len(entries) > 0:
            grades = [e.grade for e in entries]
            mean_grade = sum(grades) / len(grades)
            predicted = round(mean_grade)
            low = max(1, predicted - 1)
            high = min(7, predicted + 1)
            confidence = "low"
            trend = "stable"
        else:
            predicted = 0
            low = 0
            high = 0
            confidence = "none"
            trend = "stable"

        topics = get_syllabus_topics(s.name)
        coverage_pct = coverage_data.get(s.name, 0)

        subject_predictions.append({
            "subject": s.name,
            "level": s.level,
            "target": s.target_grade,
            "predicted": predicted,
            "low": low,
            "high": high,
            "confidence": confidence,
            "trend": trend,
            "coverage": coverage_pct,
        })

    return render_template(
        "dashboard.html",
        profile=profile,
        countdown=countdown,
        gaps=gaps,
        predicted_total=predicted_total,
        recommendation=recommendation,
        recent=recent,
        coverage_data=coverage_data,
        review_due=review_due,
        lifecycle_summary=lifecycle_summary,
        gam=gam,
        heatmap=heatmap,
        flashcard_due=flashcard_due,
        today_tasks=today_tasks,
        subject_predictions=subject_predictions,
    )


# ── Backwards compat redirects ─────────────────────────────

@bp.route("/quiz")
@login_required
def quiz_redirect():
    return redirect(url_for("study.study"))


@bp.route("/analytics")
@login_required
def analytics_redirect():
    return redirect(url_for("insights.insights"))


# ── Service Worker route (must be served from root) ────────

@bp.route("/sw.js")
def service_worker():
    return send_from_directory(
        current_app.static_folder, "sw.js",
        mimetype="application/javascript",
        max_age=0,
    )


# ── Health checks ─────────────────────────────────────────

_start_time = time.time()


@bp.route("/health")
def health():
    uptime = int(time.time() - _start_time)
    return jsonify({"status": "ok", "uptime_seconds": uptime})


@bp.route("/ready")
def ready():
    try:
        from database import get_db
        db = get_db()
        db.execute("SELECT 1").fetchone()
        return jsonify({"status": "ready"}), 200
    except Exception as exc:
        return jsonify({"status": "not_ready", "error": str(exc)}), 503


@bp.route("/live")
def live():
    return jsonify({"status": "alive"}), 200
