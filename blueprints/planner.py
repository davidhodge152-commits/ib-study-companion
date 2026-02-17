"""Study planner routes."""

from __future__ import annotations

from datetime import date, timedelta

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import login_required

from helpers import current_user_id
from profile import StudyTask, DailyPlan, XP_AWARDS
from db_stores import (
    GamificationProfileDB,
    GradeDetailLogDB,
    ReviewScheduleDB,
    StudentProfileDB,
    StudyPlanDB,
    TopicProgressStoreDB,
)
from subject_config import get_syllabus_topics

bp = Blueprint("planner", __name__)


@bp.route("/planner")
@login_required
def planner_page():
    uid = current_user_id()
    profile = StudentProfileDB.load(uid)
    if not profile:
        return redirect(url_for("core.onboarding"))

    plan_data = StudyPlanDB(uid).load()
    return render_template("planner.html", profile=profile, plan=plan_data, today=date.today().isoformat())


@bp.route("/api/planner/generate", methods=["POST"])
@login_required
def api_planner_generate():
    uid = current_user_id()
    profile = StudentProfileDB.load(uid)
    if not profile:
        return jsonify({"error": "No profile found"}), 404

    grade_log = GradeDetailLogDB(uid)
    review_sched = ReviewScheduleDB(uid)
    tp_store = TopicProgressStoreDB(uid)
    countdown = profile.exam_countdown()

    gaps = profile.compute_gaps(grade_log)
    due_items = review_sched.due_this_week()

    generated_date = date.today().isoformat()
    exam_date = countdown["exam_date"]
    daily_plans: list[DailyPlan] = []

    subject_weights: dict[str, float] = {}
    for g in gaps:
        if g["status"] == "behind":
            subject_weights[g["subject"]] = 3.0
        elif g["status"] == "close":
            subject_weights[g["subject"]] = 2.0
        elif g["status"] == "no_data":
            subject_weights[g["subject"]] = 1.5
        else:
            subject_weights[g["subject"]] = 1.0

    total_weight = sum(subject_weights.values())
    if total_weight == 0:
        total_weight = 1

    subjects_list = list(subject_weights.keys())
    daily_study_minutes = 120

    for day_offset in range(14):
        d = date.today() + timedelta(days=day_offset)
        tasks: list[StudyTask] = []

        for item in due_items:
            review_date = date.fromisoformat(item.next_review)
            if review_date <= d and review_date > d - timedelta(days=2):
                tasks.append(StudyTask(
                    subject=item.subject,
                    topic=item.topic,
                    task_type="review",
                    duration_minutes=15,
                    priority="high",
                ))
                if len(tasks) >= 2:
                    break

        remaining_minutes = daily_study_minutes - sum(t.duration_minutes for t in tasks)

        day_subject_idx = day_offset % max(len(subjects_list), 1)
        primary_subject = subjects_list[day_subject_idx] if subjects_list else ""
        secondary_idx = (day_offset + 1) % max(len(subjects_list), 1)
        secondary_subject = subjects_list[secondary_idx] if subjects_list else ""

        if primary_subject and remaining_minutes > 0:
            topics = get_syllabus_topics(primary_subject)
            topic_name = "General practice"
            task_type = "practice"
            if topics:
                tp = tp_store.get(primary_subject)
                for t in topics:
                    if not tp.topics.get(t.id):
                        topic_name = t.name
                        break

            primary_minutes = min(remaining_minutes, 60)
            weight = subject_weights.get(primary_subject, 1)
            priority = "high" if weight >= 3 else "medium" if weight >= 2 else "low"

            tasks.append(StudyTask(
                subject=primary_subject,
                topic=topic_name,
                task_type=task_type,
                duration_minutes=primary_minutes,
                priority=priority,
            ))
            remaining_minutes -= primary_minutes

        if secondary_subject and secondary_subject != primary_subject and remaining_minutes > 0:
            topics = get_syllabus_topics(secondary_subject)
            topic_name = "General practice"
            if topics:
                tp = tp_store.get(secondary_subject)
                for t in topics:
                    if not tp.topics.get(t.id):
                        topic_name = t.name
                        break

            tasks.append(StudyTask(
                subject=secondary_subject,
                topic=topic_name,
                task_type="practice",
                duration_minutes=min(remaining_minutes, 45),
                priority="medium",
            ))

        if day_offset % 3 == 0:
            tasks.append(StudyTask(
                subject="Extended Essay",
                topic="EE work session",
                task_type="ee_work",
                duration_minutes=30,
                priority="medium",
            ))

        total_mins = sum(t.duration_minutes for t in tasks)
        daily_plans.append(DailyPlan(
            date=d.isoformat(),
            tasks=tasks,
            estimated_minutes=total_mins,
        ))

    StudyPlanDB(uid).save(generated_date, exam_date, daily_plans)

    return jsonify({
        "success": True,
        "plan": {
            "generated_date": generated_date,
            "exam_date": exam_date,
            "daily_plans": [
                {
                    "date": dp.date,
                    "estimated_minutes": dp.estimated_minutes,
                    "tasks": [
                        {
                            "subject": t.subject,
                            "topic": t.topic,
                            "task_type": t.task_type,
                            "duration_minutes": t.duration_minutes,
                            "priority": t.priority,
                            "completed": t.completed,
                        }
                        for t in dp.tasks
                    ],
                }
                for dp in daily_plans
            ],
        },
    })


@bp.route("/api/planner/complete", methods=["POST"])
@login_required
def api_planner_complete():
    data = request.get_json()
    day_date = data.get("date", "")
    task_index = int(data.get("task_index", -1))

    uid = current_user_id()
    plan_db = StudyPlanDB(uid)
    result = plan_db.update_task(day_date, task_index)

    if result is None:
        return jsonify({"error": "Task not found or no plan generated yet"}), 404

    if result:
        gam = GamificationProfileDB(uid)
        gam.award_xp(XP_AWARDS["complete_planner_task"], "complete_planner_task")

    return jsonify({"completed": result})
