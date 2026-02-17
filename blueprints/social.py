"""Study groups, challenges, leaderboard, community papers, and analytics routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from helpers import current_user_id
from db_stores import (
    ChallengeStoreDB,
    CommunityPaperStoreDB,
    GamificationProfileDB,
    LeaderboardStoreDB,
    StudentProfileDB,
    StudyGroupStoreDB,
)

bp = Blueprint("social", __name__)


# ── Study Groups ──────────────────────────────────────────

@bp.route("/groups")
@login_required
def groups_page():
    uid = current_user_id()
    profile = StudentProfileDB(uid)
    gam = GamificationProfileDB(uid)
    return render_template("groups.html", profile=profile, gam=gam)


@bp.route("/api/groups", methods=["POST"])
@login_required
def api_create_group():
    uid = current_user_id()
    data = request.get_json(force=True)
    result = StudyGroupStoreDB.create(
        name=data.get("name", "Study Group"),
        created_by=uid,
        subject=data.get("subject", ""),
        level=data.get("level", ""),
        max_members=data.get("max_members", 20),
    )
    return jsonify({"success": True, **result})


@bp.route("/api/groups")
@login_required
def api_list_groups():
    uid = current_user_id()
    return jsonify({"groups": StudyGroupStoreDB.user_groups(uid)})


@bp.route("/api/groups/<int:group_id>")
@login_required
def api_get_group(group_id):
    group = StudyGroupStoreDB.get(group_id)
    if not group:
        return jsonify({"error": "Group not found"}), 404
    members = StudyGroupStoreDB.members(group_id)
    challenges = ChallengeStoreDB.group_challenges(group_id)
    return jsonify({"group": group, "members": members, "challenges": challenges})


@bp.route("/api/groups/<int:group_id>/join", methods=["POST"])
@login_required
def api_join_group(group_id):
    uid = current_user_id()
    data = request.get_json(force=True)
    invite_code = data.get("invite_code", "")
    group = StudyGroupStoreDB.get(group_id)
    if not group or group["invite_code"] != invite_code:
        return jsonify({"error": "Invalid invite code"}), 400
    ok = StudyGroupStoreDB.join(group_id, uid)
    return jsonify({"success": ok})


@bp.route("/api/groups/join", methods=["POST"])
@login_required
def api_join_group_by_code():
    uid = current_user_id()
    data = request.get_json(force=True)
    code = data.get("invite_code", "")
    group = StudyGroupStoreDB.get_by_invite(code)
    if not group:
        return jsonify({"error": "Invalid invite code"}), 404
    ok = StudyGroupStoreDB.join(group["id"], uid)
    return jsonify({"success": ok, "group_id": group["id"]})


@bp.route("/api/groups/<int:group_id>/leave", methods=["POST"])
@login_required
def api_leave_group(group_id):
    uid = current_user_id()
    StudyGroupStoreDB.leave(group_id, uid)
    return jsonify({"success": True})


# ── Challenges ──────────────────────────────────────────

@bp.route("/api/challenges", methods=["POST"])
@login_required
def api_create_challenge():
    uid = current_user_id()
    data = request.get_json(force=True)
    challenge_id = ChallengeStoreDB.create(
        group_id=data["group_id"],
        challenger_id=uid,
        title=data.get("title", "Challenge"),
        subject=data.get("subject", ""),
        config=data.get("config"),
    )
    return jsonify({"success": True, "challenge_id": challenge_id})


@bp.route("/api/challenges/<int:challenge_id>")
@login_required
def api_get_challenge(challenge_id):
    challenge = ChallengeStoreDB.get(challenge_id)
    if not challenge:
        return jsonify({"error": "Not found"}), 404
    lb = ChallengeStoreDB.leaderboard(challenge_id)
    return jsonify({"challenge": challenge, "leaderboard": lb})


@bp.route("/api/challenges/<int:challenge_id>/submit", methods=["POST"])
@login_required
def api_submit_challenge(challenge_id):
    uid = current_user_id()
    data = request.get_json(force=True)
    ok = ChallengeStoreDB.submit_score(challenge_id, uid, data.get("score", 0))
    return jsonify({"success": ok})


@bp.route("/api/leaderboard")
@login_required
def api_leaderboard():
    scope = request.args.get("scope", "global")
    scope_id = int(request.args.get("scope_id", 0))
    period = request.args.get("period", "all")
    entries = LeaderboardStoreDB.get(scope, scope_id, period)
    return jsonify({"leaderboard": entries})


# ── Community Papers ──────────────────────────────────────

@bp.route("/community")
@login_required
def community_page():
    uid = current_user_id()
    profile = StudentProfileDB(uid)
    gam = GamificationProfileDB(uid)
    return render_template("community.html", profile=profile, gam=gam)


@bp.route("/api/papers")
@login_required
def api_list_papers():
    subject = request.args.get("subject", "")
    level = request.args.get("level", "")
    papers = CommunityPaperStoreDB.list_papers(subject=subject, level=level)
    return jsonify({"papers": papers})


@bp.route("/api/papers", methods=["POST"])
@login_required
def api_upload_paper():
    uid = current_user_id()
    data = request.get_json(force=True)
    paper_id = CommunityPaperStoreDB.create(
        uploader_id=uid,
        title=data.get("title", ""),
        subject=data.get("subject", ""),
        level=data.get("level", ""),
        year=data.get("year", 0),
        session=data.get("session", ""),
        paper_number=data.get("paper_number", 0),
        questions=data.get("questions"),
    )
    return jsonify({"success": True, "paper_id": paper_id})


@bp.route("/api/papers/<int:paper_id>")
@login_required
def api_get_paper(paper_id):
    paper = CommunityPaperStoreDB.get(paper_id)
    if not paper:
        return jsonify({"error": "Not found"}), 404
    CommunityPaperStoreDB.increment_downloads(paper_id)
    return jsonify({"paper": paper})


@bp.route("/api/papers/<int:paper_id>/rate", methods=["POST"])
@login_required
def api_rate_paper(paper_id):
    uid = current_user_id()
    data = request.get_json(force=True)
    CommunityPaperStoreDB.rate(paper_id, uid, data.get("rating", 5))
    return jsonify({"success": True})


@bp.route("/api/papers/<int:paper_id>/report", methods=["POST"])
@login_required
def api_report_paper(paper_id):
    uid = current_user_id()
    data = request.get_json(force=True)
    CommunityPaperStoreDB.report(paper_id, uid, data.get("reason", ""))
    return jsonify({"success": True})


@bp.route("/api/papers/<int:paper_id>/approve", methods=["POST"])
@login_required
def api_approve_paper(paper_id):
    if not (current_user.is_authenticated and getattr(current_user, "role", "") in ("teacher", "admin")):
        return jsonify({"error": "Forbidden"}), 403
    CommunityPaperStoreDB.approve(paper_id)
    return jsonify({"success": True})


# ── Community Analytics ──────────────────────────────────────

@bp.route("/community-analytics")
def community_analytics_page():
    return render_template("analytics.html", show_sidebar=True,
                           profile=None, gam=None)


@bp.route("/api/analytics/global")
def api_analytics_global():
    try:
        from community_analytics import global_stats
        return jsonify(global_stats())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/analytics/trending")
def api_analytics_trending():
    try:
        from community_analytics import trending_topics
        return jsonify({"topics": trending_topics()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
