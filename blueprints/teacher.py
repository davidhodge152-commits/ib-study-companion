"""Teacher dashboard, classes, assignments, batch grading, and reviews routes."""

from __future__ import annotations

import json
from datetime import datetime

from flask import Blueprint, Response, abort, jsonify, render_template, request
from flask_login import login_required

from helpers import current_user_id, teacher_required
from db_stores import (
    AssignmentStoreDB,
    ClassStoreDB,
    GamificationProfileDB,
    StudentProfileDB,
)

bp = Blueprint("teacher", __name__)


# ── Teacher Dashboard ──────────────────────────────────────

@bp.route("/teacher/dashboard")
@teacher_required
def teacher_dashboard():
    uid = current_user_id()
    profile = StudentProfileDB(uid)
    gam = GamificationProfileDB(uid)
    classes = ClassStoreDB.teacher_classes(uid)
    return render_template("teacher_dashboard.html", profile=profile, gam=gam, classes=classes)


@bp.route("/teacher/classes", methods=["POST"])
@teacher_required
def teacher_create_class():
    uid = current_user_id()
    data = request.get_json(force=True)
    result = ClassStoreDB.create(
        teacher_id=uid,
        name=data.get("name", ""),
        subject=data.get("subject", ""),
        level=data.get("level", ""),
        school_id=data.get("school_id"),
    )
    return jsonify({"success": True, **result})


@bp.route("/teacher/classes/<int:class_id>")
@teacher_required
def teacher_class_detail(class_id):
    uid = current_user_id()
    cls = ClassStoreDB.get(class_id)
    if not cls or cls["teacher_id"] != uid:
        abort(404)
    profile = StudentProfileDB(uid)
    gam = GamificationProfileDB(uid)
    members = ClassStoreDB.members(class_id)
    progress = ClassStoreDB.student_progress(class_id)
    avg_grades = ClassStoreDB.class_avg_grades(class_id)
    assignments = AssignmentStoreDB.list_for_class(class_id)
    return render_template("class_detail.html", profile=profile, gam=gam,
                           cls=cls, members=members, progress=progress,
                           avg_grades=avg_grades, assignments=assignments)


@bp.route("/teacher/assignments", methods=["POST"])
@teacher_required
def teacher_create_assignment():
    data = request.get_json(force=True)
    aid = AssignmentStoreDB.create(
        class_id=data["class_id"],
        title=data.get("title", ""),
        description=data.get("description", ""),
        due_date=data.get("due_date", ""),
        config=data.get("config"),
    )
    return jsonify({"success": True, "assignment_id": aid})


@bp.route("/teacher/assignments/<int:assignment_id>/submissions")
@teacher_required
def teacher_assignment_submissions(assignment_id):
    subs = AssignmentStoreDB.submissions(assignment_id)
    return jsonify({"submissions": subs})


@bp.route("/api/teacher/stats")
@teacher_required
def api_teacher_stats():
    uid = current_user_id()
    classes = ClassStoreDB.teacher_classes(uid)
    total_students = sum(c.get("member_count", 0) for c in classes)
    return jsonify({
        "class_count": len(classes),
        "total_students": total_students,
        "classes": classes,
    })


@bp.route("/api/teacher/class/<int:class_id>/topic-gaps")
@teacher_required
def api_teacher_topic_gaps(class_id):
    uid = current_user_id()
    cls = ClassStoreDB.get(class_id)
    if not cls or cls["teacher_id"] != uid:
        abort(404)
    gaps = ClassStoreDB.topic_gaps(class_id)
    return jsonify({"topic_gaps": gaps})


@bp.route("/api/teacher/class/<int:class_id>/at-risk")
@teacher_required
def api_teacher_at_risk(class_id):
    uid = current_user_id()
    cls = ClassStoreDB.get(class_id)
    if not cls or cls["teacher_id"] != uid:
        abort(404)
    students = ClassStoreDB.at_risk_students(class_id)
    return jsonify({"at_risk_students": students})


@bp.route("/api/teacher/class/<int:class_id>/grade-distribution")
@teacher_required
def api_teacher_grade_distribution(class_id):
    uid = current_user_id()
    cls = ClassStoreDB.get(class_id)
    if not cls or cls["teacher_id"] != uid:
        abort(404)
    data = ClassStoreDB.grade_distribution(class_id)
    return jsonify({"grade_distribution": data})


@bp.route("/api/teacher/class/<int:class_id>/activity-heatmap")
@teacher_required
def api_teacher_activity_heatmap(class_id):
    uid = current_user_id()
    cls = ClassStoreDB.get(class_id)
    if not cls or cls["teacher_id"] != uid:
        abort(404)
    data = ClassStoreDB.activity_heatmap(class_id)
    return jsonify({"activity_heatmap": data})


@bp.route("/api/teacher/class/<int:class_id>/command-term-breakdown")
@teacher_required
def api_teacher_command_term_breakdown(class_id):
    uid = current_user_id()
    cls = ClassStoreDB.get(class_id)
    if not cls or cls["teacher_id"] != uid:
        abort(404)
    data = ClassStoreDB.command_term_breakdown(class_id)
    return jsonify({"command_term_breakdown": data})


@bp.route("/api/teacher/sos-alerts")
@teacher_required
def api_teacher_sos_alerts():
    uid = current_user_id()
    from database import get_db as _get_db
    db = _get_db()
    rows = db.execute(
        "SELECT sa.*, u.name as student_name "
        "FROM sos_alerts sa "
        "JOIN class_members cm ON sa.user_id = cm.user_id "
        "JOIN classes c ON cm.class_id = c.id "
        "JOIN users u ON sa.user_id = u.id "
        "WHERE c.teacher_id = ? AND sa.status = 'active' "
        "ORDER BY sa.created_at DESC",
        (uid,),
    ).fetchall()
    return jsonify({"alerts": [dict(r) for r in rows]})


@bp.route("/api/teacher/class/<int:class_id>/export")
@teacher_required
def api_teacher_export_csv(class_id):
    uid = current_user_id()
    cls = ClassStoreDB.get(class_id)
    if not cls or cls["teacher_id"] != uid:
        abort(404)
    csv_data = ClassStoreDB.export_class_csv(class_id)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=class_{class_id}_report.csv"},
    )


@bp.route("/api/admin/analytics-export")
@teacher_required
def api_admin_analytics_export():
    """Export anonymized platform analytics (teacher/admin only)."""
    from data_pipeline import export_anonymized_analytics
    from flask import current_app
    data = export_anonymized_analytics(current_app._get_current_object())
    return jsonify(data)


# ── Student class/assignment endpoints ──────────────────────

@bp.route("/api/classes/join", methods=["POST"])
@login_required
def api_join_class():
    uid = current_user_id()
    data = request.get_json(force=True)
    code = data.get("join_code", "")
    cls = ClassStoreDB.get_by_join_code(code)
    if not cls:
        return jsonify({"error": "Invalid class code"}), 404
    ok = ClassStoreDB.join(cls["id"], uid)
    return jsonify({"success": ok, "class_id": cls["id"]})


@bp.route("/api/assignments")
@login_required
def api_student_assignments():
    uid = current_user_id()
    return jsonify({"assignments": AssignmentStoreDB.student_assignments(uid)})


# ── Batch Grading ──────────────────────────────────────────

@bp.route("/api/teacher/batch-grade", methods=["POST"])
@teacher_required
def api_teacher_batch_grade():
    data = request.get_json()
    class_id = int(data.get("class_id", 0))
    subject = data.get("subject", "")
    doc_type = data.get("doc_type", "ia")
    assignment_title = data.get("assignment_title", "")
    submissions = data.get("submissions", [])
    if not class_id or not subject or not submissions:
        return jsonify({"error": "class_id, subject, and submissions required"}), 400

    uid = current_user_id()

    cls = ClassStoreDB.get(class_id)
    if not cls or cls["teacher_id"] != uid:
        abort(404)

    from credit_store import CreditStoreDB, FEATURE_COSTS
    cost_per = FEATURE_COSTS.get("batch_grade_per_student", 20)
    total_cost = cost_per * len(submissions)
    store = CreditStoreDB(uid)
    if not store.has_credits(total_cost):
        return jsonify({
            "error": "Insufficient credits",
            "required": total_cost,
            "balance": store.balance(),
        }), 402
    store.debit(total_cost, "batch_grade_per_student",
                f"Batch grade: {len(submissions)} students")

    from database import get_db as _get_db
    db = _get_db()
    now = datetime.now().isoformat()
    cur = db.execute(
        "INSERT INTO batch_grading_jobs "
        "(teacher_id, class_id, assignment_title, subject, doc_type, "
        "status, total_submissions, created_at) "
        "VALUES (?, ?, ?, ?, ?, 'processing', ?, ?)",
        (uid, class_id, assignment_title, subject, doc_type,
         len(submissions), now),
    )
    job_id = cur.lastrowid
    db.commit()

    try:
        from agents.batch_grading_agent import BatchGradingAgent
        agent = BatchGradingAgent()
        result = agent.process_batch(submissions, subject, doc_type)

        metadata = result.metadata or {}
        db.execute(
            "UPDATE batch_grading_jobs SET status = 'completed', "
            "processed_count = ?, results = ?, class_summary = ?, "
            "completed_at = ? WHERE id = ?",
            (metadata.get("processed", 0),
             json.dumps(metadata.get("results", [])),
             json.dumps(metadata.get("class_summary", {})),
             datetime.now().isoformat(), job_id),
        )
        db.commit()

        return jsonify({
            "job_id": job_id,
            "status": "completed",
            "results": metadata.get("results", []),
            "class_summary": metadata.get("class_summary", {}),
        })
    except Exception as e:
        db.execute(
            "UPDATE batch_grading_jobs SET status = 'failed' WHERE id = ?",
            (job_id,),
        )
        db.commit()
        return jsonify({"error": str(e), "job_id": job_id}), 500


@bp.route("/api/teacher/batch-grade/<int:job_id>")
@teacher_required
def api_teacher_batch_grade_status(job_id):
    uid = current_user_id()
    from database import get_db as _get_db
    db = _get_db()
    row = db.execute(
        "SELECT * FROM batch_grading_jobs WHERE id = ? AND teacher_id = ?",
        (job_id, uid),
    ).fetchone()
    if not row:
        return jsonify({"error": "Job not found"}), 404
    result = dict(row)
    for key in ("results", "class_summary"):
        try:
            result[key] = json.loads(result[key])
        except (json.JSONDecodeError, TypeError):
            pass
    return jsonify(result)


@bp.route("/api/teacher/batch-grade/history")
@teacher_required
def api_teacher_batch_grade_history():
    uid = current_user_id()
    from database import get_db as _get_db
    db = _get_db()
    rows = db.execute(
        "SELECT id, class_id, assignment_title, subject, doc_type, status, "
        "total_submissions, processed_count, created_at, completed_at "
        "FROM batch_grading_jobs WHERE teacher_id = ? "
        "ORDER BY created_at DESC",
        (uid,),
    ).fetchall()
    return jsonify({"jobs": [dict(r) for r in rows]})


# ── SOS Detection & Tutoring (teacher endpoints) ──────────────

@bp.route("/api/sos/status")
@login_required
def api_sos_status():
    uid = current_user_id()
    from sos_detector import SOSDetector
    detector = SOSDetector(uid)
    return jsonify({"alerts": detector.active_alerts()})


@bp.route("/api/sos/request-session", methods=["POST"])
@login_required
def api_sos_request_session():
    data = request.get_json()
    alert_id = int(data.get("alert_id", 0))
    if not alert_id:
        return jsonify({"error": "Alert ID required"}), 400
    uid = current_user_id()
    from sos_detector import SOSDetector
    detector = SOSDetector(uid)
    result = detector.request_session(alert_id)
    if not result["success"]:
        status = 402 if "credits" in result.get("error", "").lower() else 400
        return jsonify(result), status
    return jsonify(result)


@bp.route("/api/sos/tutor-context/<int:request_id>")
@teacher_required
def api_sos_tutor_context(request_id):
    from sos_detector import SOSDetector
    req = SOSDetector.get_tutor_request(request_id)
    if not req:
        return jsonify({"error": "Request not found"}), 404
    return jsonify(req)


@bp.route("/api/sos/complete/<int:request_id>", methods=["POST"])
@teacher_required
def api_sos_complete(request_id):
    uid = current_user_id()
    from sos_detector import SOSDetector
    SOSDetector.complete_session(request_id, uid)
    return jsonify({"success": True})


# ── Examiner Review Pipeline ──────────────────────────────────

@bp.route("/api/reviews/submit", methods=["POST"])
@login_required
def api_reviews_submit():
    data = request.get_json()
    doc_type = data.get("doc_type", "")
    subject = data.get("subject", "")
    title = data.get("title", "")
    text = data.get("text", "")
    if not all([doc_type, subject, text]):
        return jsonify({"error": "doc_type, subject, and text are required"}), 400
    uid = current_user_id()
    from examiner_pipeline import ExaminerPipeline
    pipeline = ExaminerPipeline()
    result = pipeline.submit_for_review(uid, doc_type, subject, title, text)
    if not result["success"]:
        return jsonify(result), 402
    return jsonify(result)


@bp.route("/api/reviews/mine")
@login_required
def api_reviews_mine():
    uid = current_user_id()
    from examiner_pipeline import ExaminerPipeline
    reviews = ExaminerPipeline.student_reviews(uid)
    return jsonify({"reviews": reviews})


@bp.route("/api/reviews/queue")
@teacher_required
def api_reviews_queue():
    from examiner_pipeline import ExaminerPipeline
    reviews = ExaminerPipeline.pending_reviews()
    return jsonify({"reviews": reviews})


@bp.route("/api/reviews/<int:review_id>/assign", methods=["POST"])
@teacher_required
def api_reviews_assign(review_id):
    uid = current_user_id()
    from examiner_pipeline import ExaminerPipeline
    ExaminerPipeline.assign_to_examiner(review_id, uid)
    return jsonify({"success": True})


@bp.route("/api/reviews/<int:review_id>/complete", methods=["POST"])
@teacher_required
def api_reviews_complete(review_id):
    data = request.get_json()
    feedback = data.get("feedback", "")
    grade = data.get("grade", "")
    video_url = data.get("video_url", "")
    if not feedback:
        return jsonify({"error": "Feedback required"}), 400
    from examiner_pipeline import ExaminerPipeline
    ExaminerPipeline.submit_examiner_feedback(review_id, feedback, grade, video_url)
    ExaminerPipeline.deliver_to_student(review_id)
    return jsonify({"success": True})


@bp.route("/teacher/examiner")
@teacher_required
def examiner_dashboard():
    uid = current_user_id()
    profile = StudentProfileDB(uid)
    gam = GamificationProfileDB(uid)
    return render_template("examiner_dashboard.html", profile=profile, gam=gam)


@bp.route("/api/reviews/assigned")
@teacher_required
def api_reviews_assigned():
    uid = current_user_id()
    from database import get_db as _get_db
    db = _get_db()
    rows = db.execute(
        "SELECT * FROM examiner_reviews WHERE examiner_id = ? AND status = 'assigned' "
        "ORDER BY assigned_at DESC",
        (uid,),
    ).fetchall()
    return jsonify({"reviews": [dict(r) for r in rows]})


@bp.route("/reviews")
@login_required
def student_reviews_page():
    uid = current_user_id()
    profile = StudentProfileDB(uid)
    gam = GamificationProfileDB(uid)
    return render_template("my_reviews.html", profile=profile, gam=gam)


@bp.route("/api/reviews/<int:review_id>")
@login_required
def api_reviews_detail(review_id):
    uid = current_user_id()
    from examiner_pipeline import ExaminerPipeline
    review = ExaminerPipeline.get_review(review_id)
    if not review:
        return jsonify({"error": "Review not found"}), 404
    if review["user_id"] != uid and review.get("examiner_id") != uid:
        from flask_login import current_user as cu
        if getattr(cu, "role", "student") not in ("teacher", "admin"):
            abort(403)
    return jsonify(review)
