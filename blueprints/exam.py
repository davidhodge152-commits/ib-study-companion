"""Exam simulation routes."""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request
from flask_login import login_required

logger = logging.getLogger(__name__)

from helpers import current_user_id
from extensions import EngineManager
from db_stores import ExamSessionStoreDB, StudentAbilityStoreDB

bp = Blueprint("exam", __name__)


@bp.route("/api/exam/generate", methods=["POST"])
@login_required
def api_exam_generate():
    uid = current_user_id()
    data = request.get_json(force=True)
    subject = data.get("subject", "Biology")
    level = data.get("level", "HL")
    paper_number = data.get("paper_number", 1)

    try:
        from exam_simulation import ExamPaperGenerator
        gen = ExamPaperGenerator(EngineManager.get_engine())
        paper = gen.generate_paper(subject, level, paper_number)
    except RuntimeError as e:
        logger.error("api_exam_generate config error: %s", e)
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error("api_exam_generate failed: %s", e, exc_info=True)
        return jsonify({"error": f"Failed to generate paper: {e}"}), 500

    store = ExamSessionStoreDB(uid)
    session_id = store.create(
        subject=subject, level=level, paper_number=paper_number,
        duration_minutes=paper.get("duration_minutes", 90),
        questions=paper.get("questions", []),
    )
    return jsonify({"success": True, "session_id": session_id, "paper": paper})


@bp.route("/api/exam/<int:session_id>/submit", methods=["POST"])
@login_required
def api_exam_submit(session_id):
    uid = current_user_id()
    data = request.get_json(force=True)
    store = ExamSessionStoreDB(uid)

    from exam_simulation import ExamPaperGenerator
    grade = ExamPaperGenerator.calculate_grade(
        data.get("subject", ""),
        data.get("level", "HL"),
        data.get("total_marks", 0),
        data.get("earned_marks", 0),
    )

    store.complete(
        session_id=session_id,
        answers=data.get("answers", []),
        earned_marks=data.get("earned_marks", 0),
        total_marks=data.get("total_marks", 0),
        grade=grade,
    )
    return jsonify({"success": True, "grade": grade})


@bp.route("/api/exam/<int:session_id>/results")
@login_required
def api_exam_results(session_id):
    uid = current_user_id()
    store = ExamSessionStoreDB(uid)
    session = store.get(session_id)
    if not session:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"session": session})


@bp.route("/api/exam/history")
@login_required
def api_exam_history():
    uid = current_user_id()
    store = ExamSessionStoreDB(uid)
    return jsonify({"sessions": store.list_sessions()})


@bp.route("/api/ability/<subject>")
@login_required
def api_ability_profile(subject):
    uid = current_user_id()
    store = StudentAbilityStoreDB(uid)
    profile = store.get_profile(subject)
    return jsonify({"abilities": profile})
