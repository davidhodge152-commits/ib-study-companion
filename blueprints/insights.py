"""Insights, analytics, recommendation, weakness, and boundary routes."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import login_required

from helpers import (
    current_user_id,
    generate_recommendation,
    _generate_text_insights,
)
from extensions import EngineManager
from db_stores import (
    GradeDetailLogDB,
    GradeHistoryDB,
    StudentProfileDB,
    TopicProgressStoreDB,
    WritingProfileDB,
)
from subject_config import get_subject_config, get_syllabus_topics

bp = Blueprint("insights", __name__)


@bp.route("/insights")
@login_required
def insights():
    uid = current_user_id()
    profile = StudentProfileDB.load(uid)
    if not profile:
        return redirect(url_for("core.onboarding"))
    return render_template("insights.html", profile=profile)


@bp.route("/api/insights")
@login_required
def api_insights():
    try:
        uid = current_user_id()
        grader = EngineManager.get_grader()
        analytics_data = grader.get_analytics()

        grade_history = GradeHistoryDB(uid)
        history = []
        for r in grade_history.history:
            history.append({
                "question": r["question"][:60],
                "grade": r["grade"],
                "percentage": r["percentage"],
                "mark": f"{r['mark_earned']}/{r['mark_total']}",
                "timestamp": r["timestamp"],
            })
        analytics_data["history"] = history

        grade_log = GradeDetailLogDB(uid)
        profile = StudentProfileDB.load(uid)

        ct_stats = grade_log.command_term_stats()
        analytics_data["command_term_stats"] = ct_stats
        analytics_data["subject_stats"] = grade_log.subject_stats()

        if profile:
            gaps = profile.compute_gaps(grade_log)
            analytics_data["gaps"] = gaps

            total_gap = sum(max(g["gap"], 0) for g in gaps if g["status"] != "no_data")
            allocation = []
            for g in gaps:
                if g["status"] == "no_data":
                    pct = round(100 / len(gaps)) if gaps else 0
                elif total_gap > 0:
                    pct = round((max(g["gap"], 0) / total_gap) * 100) if g["gap"] > 0 else 5
                else:
                    pct = round(100 / len(gaps)) if gaps else 0
                allocation.append({"subject": g["subject"], "percentage": pct})
            analytics_data["study_allocation"] = allocation

            insights_list = _generate_text_insights(grade_log, profile, ct_stats, gaps)
            analytics_data["insights"] = insights_list

            tp_store = TopicProgressStoreDB(uid)
            coverage = {}
            for s in profile.subjects:
                topics = get_syllabus_topics(s.name)
                if topics:
                    tp = tp_store.get(s.name)
                    topic_coverage = []
                    for t in topics:
                        practiced = len(tp.topics.get(t.id, []))
                        total = len(t.subtopics)
                        topic_coverage.append({
                            "id": t.id,
                            "name": t.name,
                            "practiced": practiced,
                            "total": total,
                            "pct": round(practiced / total * 100) if total > 0 else 0,
                            "hl_only": t.hl_only,
                        })
                    coverage[s.name] = {
                        "overall": tp.overall_coverage(topics),
                        "topics": topic_coverage,
                    }
            analytics_data["syllabus_coverage"] = coverage

        wp = WritingProfileDB(uid).load()
        if wp and wp["summary"]:
            analytics_data["writing_profile"] = {
                "summary": wp["summary"],
                "verbosity": wp["verbosity"],
                "terminology_usage": wp["terminology_usage"],
                "argument_structure": wp["argument_structure"],
                "common_patterns": wp["common_patterns"],
                "analyzed_count": wp["analyzed_count"],
            }

        return jsonify(analytics_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/insights/recommendation")
@login_required
def api_recommendation():
    uid = current_user_id()
    profile = StudentProfileDB.load(uid)
    if not profile:
        return jsonify({"error": "No profile found"}), 404
    grade_log = GradeDetailLogDB(uid)
    rec = generate_recommendation(profile, grade_log)
    return jsonify(rec)


@bp.route("/api/analytics/weakness", methods=["POST"])
@login_required
def api_weakness_report():
    try:
        grader = EngineManager.get_grader()
        report = grader.get_weakness_report()
        return jsonify({"report": report})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/boundaries/<subject>/<level>")
@login_required
def api_boundaries(subject, level):
    try:
        engine = EngineManager.get_engine()
        result = engine.fetch_latest_boundaries(subject, level)
        return jsonify({
            "subject": result.subject,
            "level": result.level,
            "session": result.session,
            "boundaries": {str(k): v for k, v in result.boundaries.items()},
            "raw_text": result.raw_text,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/subject-config/<subject>")
@login_required
def api_subject_config(subject):
    config = get_subject_config(subject)
    if not config:
        return jsonify({"error": "No config for this subject"}), 404

    assessment = config.assessment_hl
    level = request.args.get("level", "HL")
    if level == "SL":
        assessment = config.assessment_sl

    return jsonify({
        "assessment": [
            {
                "name": c.name,
                "description": c.description,
                "duration_minutes": c.duration_minutes,
                "weighting_pct": c.weighting_pct,
                "marks": c.marks,
                "hl_only": c.hl_only,
            }
            for c in assessment
        ],
        "ia_description": config.ia_description,
        "ia_word_limit": config.ia_word_limit,
        "ia_weighting_pct": config.ia_weighting_pct,
        "key_command_terms": config.key_command_terms,
        "study_strategies": config.study_strategies,
        "common_pitfalls": config.common_pitfalls,
        "category": config.category,
    })


@bp.route("/api/topics/<subject>")
@login_required
def api_topics(subject):
    topics = get_syllabus_topics(subject)
    level = request.args.get("level", "HL")

    result = []
    for t in topics:
        if t.hl_only and level == "SL":
            continue
        result.append({
            "id": t.id,
            "name": t.name,
            "subtopics": t.subtopics,
            "hl_only": t.hl_only,
        })
    return jsonify({"topics": result})


# ── Predictive Analytics Endpoints ──────────────────────────


@bp.route("/api/insights/predictions")
@login_required
def api_predictions():
    """Predicted grades per subject + total IB score."""
    try:
        uid = current_user_id()
        from predictive_analytics import PredictiveGradeModel
        model = PredictiveGradeModel()
        result = model.predict_total_ib_score(uid)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/insights/study-patterns")
@login_required
def api_study_patterns():
    """Study pattern analysis for current user."""
    try:
        uid = current_user_id()
        from predictive_analytics import PredictiveGradeModel
        model = PredictiveGradeModel()
        result = model.study_pattern_analysis(uid)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/insights/peer-ranking/<subject>")
@login_required
def api_peer_ranking(subject):
    """Peer percentile ranking for a subject."""
    try:
        uid = current_user_id()
        from community_analytics import peer_percentile
        result = peer_percentile(uid, subject)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/insights/share", methods=["POST"])
@login_required
def api_share_summary():
    """Generate a shareable summary token."""
    try:
        uid = current_user_id()
        from predictive_analytics import PredictiveGradeModel
        from database import get_db
        import json

        model = PredictiveGradeModel()
        predictions = model.predict_total_ib_score(uid)
        patterns = model.study_pattern_analysis(uid)

        profile = StudentProfileDB.load(uid)
        name = profile.name if profile else "Student"

        data = {
            "name": name,
            "predictions": predictions,
            "patterns": patterns,
            "generated_at": datetime.now().isoformat(),
        }

        token = secrets.token_urlsafe(16)
        expires_at = (datetime.now() + timedelta(days=7)).isoformat()

        db = get_db()
        db.execute(
            "INSERT INTO shared_summaries (user_id, token, data, created_at, expires_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (uid, token, json.dumps(data), datetime.now().isoformat(), expires_at),
        )
        db.commit()

        return jsonify({"token": token, "expires_at": expires_at})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/share/<token>")
def view_shared_summary(token):
    """Public shareable summary page (no auth required)."""
    import json
    from database import get_db

    db = get_db()
    row = db.execute(
        "SELECT * FROM shared_summaries WHERE token = ?", (token,)
    ).fetchone()

    if not row:
        return render_template("shared_summary.html", error="Summary not found"), 404

    if row["expires_at"] and row["expires_at"] < datetime.now().isoformat():
        return render_template("shared_summary.html", error="This summary has expired"), 410

    data = json.loads(row["data"])
    return render_template("shared_summary.html", data=data, error=None)
