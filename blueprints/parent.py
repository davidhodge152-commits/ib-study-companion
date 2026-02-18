"""Parent portal routes — student settings + token-based parent dashboard."""

from __future__ import annotations

from datetime import date

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import login_required

from helpers import (
    current_user_id,
    _generate_text_insights,
    _last_active_date,
)
from db_stores import (
    ActivityLogDB,
    GradeDetailLogDB,
    ParentConfigDB,
    StudentProfileDB,
)
from audit import log_event

bp = Blueprint("parent", __name__)


@bp.route("/settings/parent")
@login_required
def parent_settings():
    uid = current_user_id()
    profile = StudentProfileDB.load(uid)
    if not profile:
        return redirect(url_for("core.onboarding"))
    parent_config = ParentConfigDB(uid)
    return render_template("parent_settings.html", profile=profile, parent_config=parent_config)


@bp.route("/api/parent/toggle", methods=["POST"])
@login_required
def api_parent_toggle():
    data = request.get_json()
    action = data.get("action", "")
    uid = current_user_id()
    parent_config = ParentConfigDB(uid)

    if action == "enable":
        parent_config.save_all(enabled=True)
        if not parent_config.token:
            parent_config.generate_token()
            log_event("parent_token_generate", uid, "action=enable")
        profile = StudentProfileDB.load(uid)
        if profile and not parent_config.student_display_name:
            parent_config.save_all(student_display_name=profile.name)
    elif action == "disable":
        parent_config.save_all(enabled=False)
    elif action == "regenerate":
        parent_config.generate_token()
        log_event("parent_token_generate", uid, f"action={action}")

    return jsonify({
        "enabled": parent_config.enabled,
        "token": parent_config.token if parent_config.enabled else "",
    })


@bp.route("/api/parent/privacy")
@login_required
def api_parent_privacy_get():
    """Return current privacy settings for the authenticated student."""
    uid = current_user_id()
    parent_config = ParentConfigDB(uid)
    return jsonify({
        "show_subject_grades": parent_config.show_subject_grades,
        "show_recent_activity": parent_config.show_recent_activity,
        "show_study_consistency": parent_config.show_study_consistency,
        "show_insights": parent_config.show_insights,
        "show_exam_countdown": parent_config.show_exam_countdown,
    })


@bp.route("/api/parent/privacy", methods=["POST"])
@login_required
def api_parent_privacy():
    data = request.get_json()
    uid = current_user_id()
    parent_config = ParentConfigDB(uid)
    parent_config.save_all(
        student_display_name=data.get("student_display_name", parent_config.student_display_name),
        show_subject_grades=data.get("show_subject_grades", parent_config.show_subject_grades),
        show_recent_activity=data.get("show_recent_activity", parent_config.show_recent_activity),
        show_study_consistency=data.get("show_study_consistency", parent_config.show_study_consistency),
        show_command_term_stats=data.get("show_command_term_stats", parent_config.show_command_term_stats),
        show_insights=data.get("show_insights", parent_config.show_insights),
        show_exam_countdown=data.get("show_exam_countdown", parent_config.show_exam_countdown),
    )
    return jsonify({"success": True})


@bp.route("/parent/<token>")
def parent_dashboard(token):
    parent_config = ParentConfigDB.load_by_token(token)
    if not parent_config:
        return render_template("parent_404.html"), 404

    user_id = parent_config.user_id
    profile = StudentProfileDB.load(user_id)
    if not profile:
        return render_template("parent_404.html"), 404

    grade_log = GradeDetailLogDB(user_id)
    activity_log = ActivityLogDB(user_id)

    context = {
        "student_name": parent_config.student_display_name or profile.name,
        "config": parent_config,
    }

    if parent_config.show_exam_countdown:
        context["countdown"] = profile.exam_countdown()

    if parent_config.show_subject_grades:
        gaps = profile.compute_gaps(grade_log)
        context["gaps"] = gaps
        context["predicted_total"] = profile.compute_predicted_total(grade_log)
        context["target_total"] = profile.target_total_points

    if parent_config.show_recent_activity:
        context["recent_activity"] = activity_log.recent_activity(10)

    if parent_config.show_study_consistency:
        context["streak"] = activity_log.streak()
        context["days_active_30"] = activity_log.days_active_last_n(30)
        context["heatmap"] = activity_log.daily_heatmap(90)
        context["weekly_summary"] = activity_log.weekly_summary(4)

    if parent_config.show_insights:
        ct_stats = grade_log.command_term_stats()
        gaps = profile.compute_gaps(grade_log)
        context["insights"] = _generate_text_insights(grade_log, profile, ct_stats, gaps)

    alerts = []
    if parent_config.show_study_consistency:
        days_inactive = (date.today() - _last_active_date(activity_log)).days
        if days_inactive >= 7:
            alerts.append({
                "type": "warning",
                "message": f"No study activity in the last {days_inactive} days.",
            })
    if parent_config.show_subject_grades:
        gaps = profile.compute_gaps(grade_log)
        for g in gaps:
            if g["status"] == "behind" and g["gap"] >= 2:
                alerts.append({
                    "type": "concern",
                    "message": f"{g['subject']}: predicted {g['predicted']}, target {g['target']} ({g['gap']:+d} gap).",
                })
    context["alerts"] = alerts

    return render_template("parent_dashboard.html", **context)


@bp.route("/api/parent/traffic-light/<token>")
def api_parent_traffic_light(token):
    parent_config = ParentConfigDB.load_by_token(token)
    if not parent_config or not parent_config.enabled:
        return jsonify({"error": "Invalid or disabled parent link"}), 404
    from parent_analytics import ParentAnalytics
    analytics = ParentAnalytics(parent_config.user_id)
    result = analytics.traffic_light()
    result["sos_highlights"] = analytics.sos_highlights()
    result["action_items"] = analytics.action_items()
    return jsonify(result)


@bp.route("/api/parent/digest/<token>")
def api_parent_digest(token):
    parent_config = ParentConfigDB.load_by_token(token)
    if not parent_config or not parent_config.enabled:
        return jsonify({"error": "Invalid or disabled parent link"}), 404
    from parent_analytics import ParentAnalytics
    analytics = ParentAnalytics(parent_config.user_id)
    return jsonify(analytics.weekly_digest())
