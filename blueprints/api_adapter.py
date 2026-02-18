"""
JSON API adapter for the Next.js SPA frontend.

Bridges the gap between React frontend API calls and the existing
Flask service layer. All endpoints return JSON and accept JSON bodies.
"""

from __future__ import annotations

import json
import math
import secrets
from datetime import date, datetime, timedelta

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from audit import log_event
from database import get_db
from helpers import current_user_id, generate_recommendation, paginate_args, paginated_response
from profile import IB_SUBJECTS, SubjectEntry
from subject_config import get_syllabus_topics
from db_stores import (
    ActivityLogDB,
    FlashcardDeckDB,
    GamificationProfileDB,
    GradeDetailLogDB,
    IBLifecycleDB,
    NotificationStoreDB,
    ReviewScheduleDB,
    StudentProfileDB,
    StudyPlanDB,
    TopicProgressStoreDB,
)

bp = Blueprint("api_adapter", __name__)

LOCKOUT_THRESHOLD = 5
LOCKOUT_MINUTES = 15


# ── Auth ─────────────────────────────────────────────────────

@bp.route("/api/auth/me")
def auth_me():
    """Return current authenticated user or 401."""
    if not current_user.is_authenticated:
        return jsonify({"error": "Not authenticated"}), 401
    return jsonify({
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": getattr(current_user, "role", "student"),
    })


@bp.route("/api/auth/login", methods=["POST"])
def auth_login():
    """JSON login — accepts {email, password}, sets session cookie."""
    if current_user.is_authenticated:
        return jsonify({"success": True})

    data = request.get_json(force=True)
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    from auth import User
    row = User.get_by_email(email)
    if not row:
        return jsonify({"error": "Invalid email or password."}), 401

    # Check lockout
    locked_until = row["locked_until"] if "locked_until" in row.keys() else ""
    if locked_until:
        try:
            lock_time = datetime.fromisoformat(locked_until)
            remaining = (lock_time - datetime.now()).total_seconds()
            if remaining > 0:
                mins = math.ceil(remaining / 60)
                return jsonify({
                    "error": f"Account temporarily locked. Try again in {mins} minute(s)."
                }), 429
        except (ValueError, TypeError):
            pass

    if not row["password_hash"] or not check_password_hash(row["password_hash"], password):
        db = get_db()
        attempts = (row["login_attempts"] if "login_attempts" in row.keys() else 0) + 1
        if attempts >= LOCKOUT_THRESHOLD:
            db.execute(
                "UPDATE users SET login_attempts=?, locked_until=? WHERE id=?",
                (attempts, (datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)).isoformat(), row["id"]),
            )
        else:
            db.execute("UPDATE users SET login_attempts=? WHERE id=?", (attempts, row["id"]))
        db.commit()
        log_event("login_failed", row["id"], f"email={email} attempts={attempts}")
        return jsonify({"error": "Invalid email or password."}), 401

    # Check email verification
    email_verified = row["email_verified"] if "email_verified" in row.keys() else 1
    if not email_verified:
        return jsonify({
            "error": "Please verify your email address. Check your inbox for the verification link."
        }), 403

    # Success
    db = get_db()
    db.execute("UPDATE users SET login_attempts=0, locked_until='' WHERE id=?", (row["id"],))
    db.commit()

    role = row["role"] if "role" in row.keys() else "student"
    user = User(row["id"], row["name"], row["email"], role)
    login_user(user, remember=True)
    log_event("login_success", row["id"])
    return jsonify({"success": True})


@bp.route("/api/auth/register", methods=["POST"])
def auth_register():
    """JSON registration — accepts {name, email, password}."""
    if current_user.is_authenticated:
        return jsonify({"success": True})

    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name or not email or not password:
        return jsonify({"error": "All fields are required."}), 400

    from auth import _validate_password, User
    pw_error = _validate_password(password)
    if pw_error:
        return jsonify({"error": pw_error}), 400

    existing = User.get_by_email(email)
    if existing:
        return jsonify({"error": "An account with this email already exists."}), 409

    db = get_db()
    cur = db.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (name, email, generate_password_hash(password), datetime.now().isoformat()),
    )
    user_id = cur.lastrowid
    db.execute("INSERT OR IGNORE INTO gamification (user_id) VALUES (?)", (user_id,))
    # Auto-verify email when no email backend is configured
    from flask import current_app
    if current_app.config.get("EMAIL_BACKEND", "log") == "log":
        db.execute("UPDATE users SET email_verified = 1 WHERE id = ?", (user_id,))
    db.commit()

    log_event("register", user_id, f"email={email}")

    # Auto-login after registration
    user = User(user_id, name, email, "student")
    login_user(user, remember=True)
    return jsonify({"success": True}), 201


@bp.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    """JSON logout — clears session."""
    uid = current_user.id if current_user.is_authenticated else None
    log_event("logout", uid)
    logout_user()
    return jsonify({"success": True})


@bp.route("/api/auth/forgot-password", methods=["POST"])
def auth_forgot_password():
    """JSON forgot password — accepts {email}."""
    data = request.get_json(force=True)
    email = (data.get("email") or "").strip().lower()

    from auth import User
    row = User.get_by_email(email) if email else None

    if row:
        token = secrets.token_urlsafe(32)
        token_hash = generate_password_hash(token)
        expires = (datetime.now() + timedelta(hours=1)).isoformat()
        db = get_db()
        db.execute(
            "UPDATE users SET reset_token=?, reset_token_expires=? WHERE id=?",
            (token_hash, expires, row["id"]),
        )
        db.commit()

        from flask import current_app
        from email_service import EmailService
        base = current_app.config.get("BASE_URL", "http://localhost:5001")
        reset_url = f"{base}/reset-password?id={row['id']}&token={token}"
        EmailService.send(
            email,
            "Password Reset — IB Study Companion",
            f"<p>Click the link below to reset your password (expires in 1 hour):</p>"
            f'<p><a href="{reset_url}">{reset_url}</a></p>',
        )
        log_event("password_reset_request", row["id"])

    # Always return success to prevent email enumeration
    return jsonify({"success": True})


@bp.route("/api/auth/reset-password", methods=["POST"])
def auth_reset_password():
    """JSON reset password — accepts {token, password} or {user_id, token, password}."""
    data = request.get_json(force=True)
    user_id = data.get("user_id") or data.get("id")
    token = data.get("token") or ""
    password = data.get("password") or ""

    if not user_id or not token or not password:
        return jsonify({"error": "Missing required fields."}), 400

    from auth import _validate_password
    pw_error = _validate_password(password)
    if pw_error:
        return jsonify({"error": pw_error}), 400

    db = get_db()
    row = db.execute(
        "SELECT id, reset_token, reset_token_expires FROM users WHERE id=?",
        (user_id,),
    ).fetchone()

    if not row or not row["reset_token"]:
        return jsonify({"error": "Invalid or expired reset link."}), 400

    if not check_password_hash(row["reset_token"], token):
        return jsonify({"error": "Invalid or expired reset link."}), 400

    try:
        expires = datetime.fromisoformat(row["reset_token_expires"])
        if datetime.now() > expires:
            return jsonify({"error": "This reset link has expired."}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid or expired reset link."}), 400

    db.execute(
        "UPDATE users SET password_hash=?, reset_token='', reset_token_expires='', "
        "login_attempts=0, locked_until='' WHERE id=?",
        (generate_password_hash(password), user_id),
    )
    db.commit()
    log_event("password_reset_complete", user_id)
    return jsonify({"success": True})


# ── Profile ──────────────────────────────────────────────────

@bp.route("/api/profile")
@login_required
def get_profile():
    """Return student profile with subjects."""
    uid = current_user_id()
    profile = StudentProfileDB.load(uid)
    if not profile:
        return jsonify({"error": "No profile found. Complete onboarding first."}), 404

    return jsonify({
        "name": profile.name,
        "exam_session": profile.exam_session,
        "target_total_points": profile.target_total_points,
        "subjects": [
            {
                "name": s.name,
                "level": s.level,
                "target_grade": s.target_grade,
            }
            for s in profile.subjects
        ],
    })


@bp.route("/api/gamification/status")
@login_required
def gamification_status():
    """Return gamification data (XP, streak, badges)."""
    uid = current_user_id()
    gam = GamificationProfileDB(uid)
    activity_log = ActivityLogDB(uid)
    gam.update_streak(activity_log)

    return jsonify({
        "total_xp": gam.total_xp,
        "daily_xp_today": gam.daily_xp_today,
        "daily_goal_xp": gam.daily_goal_xp,
        "current_streak": gam.current_streak,
        "longest_streak": gam.longest_streak,
        "badges": gam.badges,
        "total_questions_answered": gam.total_questions_answered,
        "total_flashcards_reviewed": gam.total_flashcards_reviewed,
    })


# ── Dashboard ────────────────────────────────────────────────

@bp.route("/api/dashboard")
@login_required
def dashboard_data():
    """Return all dashboard data as JSON (mirrors core.dashboard template context)."""
    uid = current_user_id()
    profile = StudentProfileDB.load(uid)
    if not profile:
        return jsonify({"error": "No profile. Complete onboarding."}), 404

    grade_log = GradeDetailLogDB(uid)
    gam = GamificationProfileDB(uid)
    activity_log = ActivityLogDB(uid)
    gam.update_streak(activity_log)

    # Stats
    total_questions = gam.total_questions_answered
    avg_grade = 0
    entries = grade_log.entries
    if entries:
        avg_grade = round(sum(e.percentage for e in entries) / len(entries))

    stats = {
        "streak": gam.current_streak,
        "total_questions": total_questions,
        "avg_grade": avg_grade,
        "xp": gam.total_xp,
        "daily_xp": gam.daily_xp_today,
        "daily_goal": gam.daily_goal_xp,
    }

    # Recent activity
    recent_activity = []
    for e in grade_log.recent(10):
        recent_activity.append({
            "type": "study",
            "title": f"{e.subject_display} — {e.command_term}",
            "description": f"Grade {e.grade} ({e.percentage}%)",
            "timestamp": e.timestamp,
        })

    # Progress data (last 30 days of grades)
    progress = []
    daily_data: dict[str, list] = {}
    for e in entries:
        day = e.timestamp[:10] if e.timestamp else ""
        if day:
            daily_data.setdefault(day, []).append(e.percentage)

    for day in sorted(daily_data.keys())[-30:]:
        pcts = daily_data[day]
        progress.append({
            "date": day,
            "average": round(sum(pcts) / len(pcts)),
            "count": len(pcts),
        })

    # Heatmap for streak display
    heatmap = activity_log.daily_heatmap(90)

    return jsonify({
        "stats": stats,
        "recent_activity": recent_activity,
        "progress": progress,
        "heatmap": heatmap,
    })


# ── Onboarding ───────────────────────────────────────────────

@bp.route("/api/onboarding", methods=["POST"])
@login_required
def onboarding_submit():
    """JSON onboarding — accepts {name, exam_session, subjects: [{name, level, target}]}."""
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    exam_session = (data.get("exam_session") or "").strip()
    raw_subjects = data.get("subjects") or []

    if not name or not raw_subjects:
        return jsonify({"error": "Name and at least one subject are required."}), 400

    subjects = []
    for s in raw_subjects:
        if s.get("name"):
            subjects.append(SubjectEntry(
                name=s["name"].strip(),
                level=s.get("level", "HL"),
                target_grade=int(s.get("target", s.get("target_grade", 5))),
            ))

    if not subjects:
        return jsonify({"error": "At least one subject is required."}), 400

    uid = current_user_id()
    existing = StudentProfileDB.load(uid)
    if existing:
        existing.save_fields(
            name=name,
            subjects=subjects,
            exam_session=exam_session,
        )
    else:
        StudentProfileDB.create(
            name=name,
            subjects=subjects,
            exam_session=exam_session,
        )

    lifecycle = IBLifecycleDB(uid)
    lifecycle.init_from_profile([s.name for s in subjects])

    return jsonify({"success": True})


# ── Subjects / Topics ────────────────────────────────────────

@bp.route("/api/subjects")
@login_required
def list_subjects():
    """Return user's enrolled subjects."""
    uid = current_user_id()
    profile = StudentProfileDB.load(uid)
    if not profile:
        return jsonify({"subjects": list(IB_SUBJECTS)})

    return jsonify({
        "subjects": [s.name for s in profile.subjects],
    })


@bp.route("/api/subjects/<subject>/topics")
@login_required
def list_topics(subject):
    """Return syllabus topics for a subject."""
    topics = get_syllabus_topics(subject)
    if not topics:
        return jsonify({"topics": []})

    return jsonify({
        "topics": [{"id": t.id, "name": t.name} for t in topics],
    })


# ── Flashcards ───────────────────────────────────────────────

@bp.route("/api/flashcards/decks")
@login_required
def flashcard_decks():
    """Return flashcard decks grouped by subject."""
    uid = current_user_id()
    fc = FlashcardDeckDB(uid)

    # Group cards by subject into virtual "decks"
    decks_map: dict[str, dict] = {}
    for card in fc.cards:
        subj = card.subject or "General"
        if subj not in decks_map:
            decks_map[subj] = {
                "id": subj,
                "name": subj,
                "subject": subj,
                "card_count": 0,
                "due_count": 0,
            }
        decks_map[subj]["card_count"] += 1
        if card.next_review and card.next_review <= date.today().isoformat():
            decks_map[subj]["due_count"] += 1

    return jsonify({"decks": list(decks_map.values())})


@bp.route("/api/flashcards/decks/<deck_id>")
@login_required
def flashcard_deck_detail(deck_id):
    """Return cards in a specific deck (subject)."""
    uid = current_user_id()
    fc = FlashcardDeckDB(uid)

    cards = [
        {
            "id": c.id,
            "front": c.front,
            "back": c.back,
            "subject": c.subject,
            "topic": c.topic,
            "interval_days": c.interval_days,
            "next_review": c.next_review,
            "review_count": c.review_count,
        }
        for c in fc.cards
        if c.subject == deck_id
    ]

    return jsonify({
        "deck": {"id": deck_id, "name": deck_id, "subject": deck_id},
        "cards": cards,
    })


@bp.route("/api/flashcards/due")
@login_required
def flashcards_due():
    """Return cards due for review, optionally filtered by deck."""
    uid = current_user_id()
    fc = FlashcardDeckDB(uid)
    deck_id = request.args.get("deck_id")
    today = date.today().isoformat()

    cards = []
    for c in fc.cards:
        if c.next_review and c.next_review <= today:
            if deck_id and c.subject != deck_id:
                continue
            cards.append({
                "id": c.id,
                "front": c.front,
                "back": c.back,
                "subject": c.subject,
                "topic": c.topic,
            })

    return jsonify({"cards": cards})


# ── Notifications ────────────────────────────────────────────
# Existing /api/notifications in notifications.py already returns JSON.
# The frontend calls /api/notifications/read-all but backend has /api/notifications/read.
# Add an alias:

@bp.route("/api/notifications/read-all", methods=["POST"])
@login_required
def mark_all_notifications_read():
    """Alias for /api/notifications/read — marks all as read."""
    uid = current_user_id()
    store = NotificationStoreDB(uid)
    store.mark_all_read()
    return jsonify({"success": True})


# ── Insights ─────────────────────────────────────────────────
# Existing /api/insights in insights.py already returns JSON with analytics data.
# No adapter needed — the frontend hook (useInsights) will use the existing endpoint.


# ── Planner ──────────────────────────────────────────────────

@bp.route("/api/planner/tasks")
@login_required
def planner_tasks():
    """Return study plan tasks."""
    uid = current_user_id()
    plan_data = StudyPlanDB(uid).load()

    tasks = []
    if plan_data:
        for dp in plan_data["daily_plans"]:
            for i, t in enumerate(dp.tasks):
                tasks.append({
                    "id": f"{dp.date}_{i}",
                    "date": dp.date,
                    "subject": t.subject,
                    "topic": t.topic,
                    "task_type": t.task_type,
                    "duration_minutes": t.duration_minutes,
                    "priority": t.priority,
                    "completed": t.completed,
                })

    return jsonify({"tasks": tasks})


@bp.route("/api/planner/tasks/<task_id>", methods=["PATCH"])
@login_required
def toggle_planner_task(task_id):
    """Toggle a planner task's completed status."""
    uid = current_user_id()
    data = request.get_json(force=True)
    completed = data.get("completed", False)

    plan_db = StudyPlanDB(uid)
    plan_data = plan_db.load()
    if not plan_data:
        return jsonify({"error": "No study plan found."}), 404

    # Parse task_id = "date_index"
    parts = task_id.rsplit("_", 1)
    if len(parts) != 2:
        return jsonify({"error": "Invalid task ID."}), 400

    target_date, idx_str = parts
    try:
        idx = int(idx_str)
    except ValueError:
        return jsonify({"error": "Invalid task ID."}), 400

    for dp in plan_data["daily_plans"]:
        if dp.date == target_date and idx < len(dp.tasks):
            dp.tasks[idx].completed = completed
            plan_db.save(plan_data)
            return jsonify({"success": True})

    return jsonify({"error": "Task not found."}), 404


@bp.route("/api/planner/generate", methods=["POST"])
@login_required
def generate_study_plan():
    """Generate a new AI study plan."""
    uid = current_user_id()
    try:
        from agents.executive_agent import ExecutiveAgent
        from extensions import EngineManager
        agent = ExecutiveAgent(EngineManager.get_engine())
        result = agent.generate_smart_plan(user_id=uid)
        return jsonify({"success": True, "response": result.content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Documents ────────────────────────────────────────────────

@bp.route("/api/documents")
@login_required
def list_documents():
    """Return uploaded documents."""
    uid = current_user_id()
    db = get_db()
    rows = db.execute(
        "SELECT id, filename, doc_type, subject, level, chunks, uploaded_at "
        "FROM uploads WHERE user_id = ? ORDER BY uploaded_at DESC",
        (uid,),
    ).fetchall()

    return jsonify({
        "documents": [dict(r) for r in rows],
    })


# ── Account ──────────────────────────────────────────────────

@bp.route("/api/account/profile", methods=["PATCH"])
@login_required
def update_account_profile():
    """Update user name and email."""
    uid = current_user_id()
    data = request.get_json(force=True)
    name = data.get("name")
    email = data.get("email")

    db = get_db()
    updates = []
    params = []

    if name:
        updates.append("name = ?")
        params.append(name.strip())
        # Also update student profile
        profile = StudentProfileDB.load(uid)
        if profile:
            profile.save_fields(name=name.strip())

    if email:
        email = email.strip().lower()
        # Check for duplicate
        existing = db.execute(
            "SELECT id FROM users WHERE email = ? AND id != ?", (email, uid)
        ).fetchone()
        if existing:
            return jsonify({"error": "Email already in use."}), 409
        updates.append("email = ?")
        params.append(email)

    if not updates:
        return jsonify({"error": "No fields to update."}), 400

    params.append(uid)
    db.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
    db.commit()
    return jsonify({"success": True})


@bp.route("/api/account/change-password", methods=["POST"])
@login_required
def change_password():
    """Change password — accepts {currentPassword, newPassword}."""
    uid = current_user_id()
    data = request.get_json(force=True)
    current_pw = data.get("currentPassword") or ""
    new_pw = data.get("newPassword") or ""

    if not current_pw or not new_pw:
        return jsonify({"error": "Both current and new password are required."}), 400

    db = get_db()
    row = db.execute("SELECT password_hash FROM users WHERE id = ?", (uid,)).fetchone()
    if not row or not check_password_hash(row["password_hash"], current_pw):
        return jsonify({"error": "Current password is incorrect."}), 403

    from auth import _validate_password
    pw_error = _validate_password(new_pw)
    if pw_error:
        return jsonify({"error": pw_error}), 400

    db.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (generate_password_hash(new_pw), uid),
    )
    db.commit()
    return jsonify({"success": True})


# ── Community (maps /api/community/posts → community_papers) ─

@bp.route("/api/community/posts")
@login_required
def community_posts():
    """Return community papers as paginated posts."""
    page, limit = paginate_args()
    db = get_db()

    total = db.execute("SELECT COUNT(*) as c FROM community_papers").fetchone()["c"]
    offset = (page - 1) * limit

    rows = db.execute(
        "SELECT cp.*, u.name as author_name "
        "FROM community_papers cp "
        "LEFT JOIN users u ON cp.uploader_id = u.id "
        "ORDER BY cp.created_at DESC LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()

    items = []
    for r in rows:
        items.append({
            "id": r["id"],
            "title": r["title"],
            "subject": r["subject"],
            "level": r["level"],
            "author": r["author_name"] or "Anonymous",
            "created_at": r["created_at"],
            "download_count": r["download_count"],
        })

    return jsonify({
        "items": items,
        "total": total,
        "page": page,
        "per_page": limit,
        "has_more": (page * limit) < total,
    })


@bp.route("/api/community/post", methods=["POST"])
@login_required
def create_community_post():
    """Create a new community paper."""
    uid = current_user_id()
    data = request.get_json(force=True)

    db = get_db()
    db.execute(
        "INSERT INTO community_papers (uploader_id, title, subject, level, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (uid, data.get("title", ""), data.get("subject", ""),
         data.get("level", ""), datetime.now().isoformat()),
    )
    db.commit()
    return jsonify({"success": True})


@bp.route("/api/community/posts/<int:post_id>/vote", methods=["POST"])
@login_required
def vote_community_post(post_id):
    """Rate a community paper."""
    uid = current_user_id()
    data = request.get_json(force=True)
    vote = data.get("vote", 1)

    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO paper_ratings (paper_id, user_id, rating, created_at) "
        "VALUES (?, ?, ?, ?)",
        (post_id, uid, vote, datetime.now().isoformat()),
    )
    db.commit()
    return jsonify({"success": True})


# ── Groups ───────────────────────────────────────────────────

@bp.route("/api/groups/create", methods=["POST"])
@login_required
def create_group():
    """Create a study group — accepts {name, description, subject}."""
    uid = current_user_id()
    data = request.get_json(force=True)
    name = data.get("name", "").strip()
    subject = data.get("subject", "")

    if not name:
        return jsonify({"error": "Group name is required."}), 400

    invite_code = secrets.token_urlsafe(6)
    db = get_db()
    cur = db.execute(
        "INSERT INTO study_groups (name, subject, created_by, invite_code, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (name, subject, uid, invite_code, datetime.now().isoformat()),
    )
    group_id = cur.lastrowid
    db.execute(
        "INSERT INTO group_members (group_id, user_id, role, joined_at) VALUES (?, ?, 'admin', ?)",
        (group_id, uid, datetime.now().isoformat()),
    )
    db.commit()
    return jsonify({"success": True, "group_id": group_id, "invite_code": invite_code})
