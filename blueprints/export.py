"""PDF report, CSV export, and question sharing routes."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, date

from flask import Blueprint, Response, jsonify, request
from flask_login import login_required

from helpers import current_user_id
from audit import log_event
from db_stores import (
    GradeDetailLogDB,
    ActivityLogDB,
    GamificationProfileDB,
    TopicProgressStoreDB,
    MisconceptionLogDB,
    SharedQuestionStoreDB,
    StudentProfileDB,
)

bp = Blueprint("export", __name__)


@bp.route("/api/export/report")
@login_required
def api_export_report():
    """Generate and return a PDF progress report."""
    uid = current_user_id()
    profile = StudentProfileDB.load(uid)
    if not profile:
        return jsonify({"error": "No profile found"}), 404

    from export import generate_pdf_report

    grade_log = GradeDetailLogDB(uid)
    activity_log = ActivityLogDB(uid)
    gam = GamificationProfileDB(uid)
    tp_store = TopicProgressStoreDB(uid)
    misc_log = MisconceptionLogDB(uid)

    pdf_bytes = generate_pdf_report(
        profile=profile,
        grade_log=grade_log,
        activity_log=activity_log,
        gamification=gam,
        topic_progress=tp_store,
        misconception_log=misc_log,
    )

    log_event("data_export", uid, "type=pdf_report")
    safe_name = profile.name.replace(" ", "_")
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="IB_Progress_Report_{safe_name}_{date.today().isoformat()}.pdf"'
        },
    )


@bp.route("/api/export/grades")
@login_required
def api_export_grades():
    """Export grade history as CSV."""
    uid = current_user_id()
    grade_log = GradeDetailLogDB(uid)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Date", "Subject", "Level", "Command Term", "Topic",
        "Mark Earned", "Mark Total", "Percentage", "Grade",
        "Strengths", "Improvements", "Examiner Tip",
    ])

    log_event("data_export", uid, "type=grades_csv")
    for e in grade_log.entries:
        writer.writerow([
            e.timestamp[:10] if e.timestamp else "",
            e.subject_display, e.level, e.command_term, e.topic,
            e.mark_earned, e.mark_total, e.percentage, e.grade,
            "; ".join(e.strengths), "; ".join(e.improvements), e.examiner_tip,
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="IB_Grades_{date.today().isoformat()}.csv"'
        },
    )


@bp.route("/api/questions/export", methods=["POST"])
@login_required
def api_questions_export():
    """Export a question set as shareable JSON."""
    data = request.get_json()
    title = data.get("title", "Shared Questions")
    description = data.get("description", "")
    questions = data.get("questions", [])
    subject = data.get("subject", "")
    topic = data.get("topic", "")
    level = data.get("level", "HL")

    if not questions:
        return jsonify({"error": "No questions to export"}), 400

    uid = current_user_id()
    profile = StudentProfileDB.load(uid)
    author = profile.name if profile else "Anonymous"

    store = SharedQuestionStoreDB(uid)
    qset = store.export_set(title, description, subject, topic, level, questions, author)

    return jsonify({
        "success": True,
        "json_data": json.loads(store.to_json(qset.id)),
    })


@bp.route("/api/questions/import", methods=["POST"])
@login_required
def api_questions_import():
    """Import a question set from JSON."""
    data = request.get_json()

    required = ["questions", "subject"]
    if not all(k in data for k in required):
        return jsonify({"error": "Invalid question set format"}), 400

    if not data.get("questions") or len(data["questions"]) == 0:
        return jsonify({"error": "No questions in set"}), 400

    uid = current_user_id()
    store = SharedQuestionStoreDB(uid)
    qset = store.import_set({
        "id": data.get("id", f"imported_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
        "title": data.get("title", "Imported Questions"),
        "description": data.get("description", ""),
        "author": data.get("author", "Unknown"),
        "subject": data["subject"],
        "topic": data.get("topic", ""),
        "level": data.get("level", "HL"),
        "questions": data["questions"],
        "created_at": data.get("created_at", datetime.now().isoformat()),
    })

    return jsonify({
        "success": True,
        "set_id": qset.id,
        "question_count": len(qset.questions),
    })


@bp.route("/api/questions/shared")
@login_required
def api_shared_questions():
    """List all shared/imported question sets."""
    uid = current_user_id()
    store = SharedQuestionStoreDB(uid)
    from dataclasses import asdict
    return jsonify({
        "sets": [asdict(qs) for qs in store.sets],
    })
