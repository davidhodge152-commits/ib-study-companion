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
    SharedFlashcardDeckDB,
    StudentProfileDB,
    StudyBuddyDB,
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
    from helpers import paginate_args, paginated_response
    uid = current_user_id()
    page, limit = paginate_args(default_limit=20)
    groups = StudyGroupStoreDB.user_groups(uid)
    total = len(groups)
    start = (page - 1) * limit
    result = paginated_response(groups[start:start + limit], total, page, limit)
    result["groups"] = result.pop("items")
    return jsonify(result)


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
    from helpers import paginate_args, paginated_response
    scope = request.args.get("scope", "global")
    scope_id = int(request.args.get("scope_id", 0))
    period = request.args.get("period", "all")
    page, limit = paginate_args(default_limit=50)
    entries = LeaderboardStoreDB.get(scope, scope_id, period, limit=limit * page)
    total = len(entries)
    start = (page - 1) * limit
    result = paginated_response(entries[start:start + limit], total, page, limit)
    result["leaderboard"] = result.pop("items")
    return jsonify(result)


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


# ── Shared Flashcard Decks ──────────────────────────────────────

@bp.route("/api/flashcards/share", methods=["POST"])
@login_required
def api_share_flashcards():
    uid = current_user_id()
    data = request.get_json(force=True)
    title = data.get("title", "")
    subject = data.get("subject", "")
    if not title or not subject:
        return jsonify({"error": "Title and subject are required"}), 400
    deck_id = SharedFlashcardDeckDB.share(
        user_id=uid,
        title=title,
        subject=subject,
        topic=data.get("topic", ""),
        description=data.get("description", ""),
        cards=data.get("cards", []),
    )
    return jsonify({"success": True, "deck_id": deck_id})


@bp.route("/api/flashcards/shared")
@login_required
def api_list_shared_flashcards():
    from helpers import paginate_args, paginated_response
    subject = request.args.get("subject", "")
    topic = request.args.get("topic", "")
    page, limit = paginate_args(default_limit=20)
    decks = SharedFlashcardDeckDB.list_decks(subject=subject, topic=topic, limit=limit * page)
    total = len(decks)
    start = (page - 1) * limit
    result = paginated_response(decks[start:start + limit], total, page, limit)
    result["decks"] = result.pop("items")
    return jsonify(result)


@bp.route("/api/flashcards/shared/<int:deck_id>")
@login_required
def api_get_shared_flashcard(deck_id):
    deck = SharedFlashcardDeckDB.get(deck_id)
    if not deck:
        return jsonify({"error": "Deck not found"}), 404
    return jsonify({"deck": deck})


@bp.route("/api/flashcards/shared/<int:deck_id>/import", methods=["POST"])
@login_required
def api_import_shared_flashcard(deck_id):
    uid = current_user_id()
    count = SharedFlashcardDeckDB.import_deck(deck_id, uid)
    return jsonify({"success": True, "imported_count": count})


# ── Study Buddy ──────────────────────────────────────

@bp.route("/api/buddy/preferences", methods=["POST"])
@login_required
def api_buddy_preferences():
    uid = current_user_id()
    data = request.get_json(force=True)
    StudyBuddyDB.save_preferences(
        user_id=uid,
        subjects=data.get("subjects", []),
        availability=data.get("availability", ""),
        timezone=data.get("timezone", ""),
        looking_for=data.get("looking_for", "study_partner"),
    )
    return jsonify({"success": True})


@bp.route("/api/buddy/matches")
@login_required
def api_buddy_matches():
    from helpers import paginate_args, paginated_response
    uid = current_user_id()
    page, limit = paginate_args(default_limit=10)
    matches = StudyBuddyDB.find_matches(uid, limit=limit * page)
    total = len(matches)
    start = (page - 1) * limit
    result = paginated_response(matches[start:start + limit], total, page, limit)
    result["matches"] = result.pop("items")
    return jsonify(result)


@bp.route("/api/buddy/connect", methods=["POST"])
@login_required
def api_buddy_connect():
    uid = current_user_id()
    data = request.get_json(force=True)
    target_id = data.get("user_id")
    if not target_id:
        return jsonify({"error": "user_id required"}), 400
    from db_stores import NotificationStoreDB
    from profile import Notification
    from datetime import datetime
    store = NotificationStoreDB(int(target_id))
    notif = Notification(
        id=f"buddy_{uid}_{target_id}",
        type="study_buddy_request",
        title="Study buddy request!",
        body=f"A student wants to study with you.",
        created_at=datetime.now().isoformat(),
        action_url="/groups",
        data={"from_user_id": uid},
    )
    store.add(notif)
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
