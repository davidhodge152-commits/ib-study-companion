"""
JSON API adapter for the Next.js SPA frontend.

Bridges the gap between React frontend API calls and the existing
Flask service layer. All endpoints return JSON and accept JSON bodies.
"""

from __future__ import annotations

import json
import logging
import math
import secrets
from datetime import date, datetime, timedelta

logger = logging.getLogger(__name__)

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

    db = get_db()
    row = db.execute(
        "SELECT id, name, email, role, created_at, locale, email_verified FROM users WHERE id = ?",
        (current_user.id,),
    ).fetchone()
    if not row:
        return jsonify({"error": "Not authenticated"}), 401

    # Check subscription plan and credits
    plan = "free"
    credits = 0
    try:
        sub = db.execute(
            "SELECT plan_id FROM user_subscriptions WHERE user_id = ?",
            (current_user.id,),
        ).fetchone()
        if sub:
            plan = sub["plan_id"] or "free"
        cred = db.execute(
            "SELECT balance FROM credit_balances WHERE user_id = ?",
            (current_user.id,),
        ).fetchone()
        if cred:
            credits = cred["balance"] or 0
    except Exception:
        try:
            db.execute("ROLLBACK")
        except Exception:
            pass

    # Get exam_session from student profile
    profile = StudentProfileDB.load(current_user.id)
    exam_session = profile.exam_session if profile else ""

    return jsonify({
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "role": row["role"] or "student",
        "exam_session": exam_session,
        "plan": plan,
        "credits": credits,
        "created_at": row["created_at"] or "",
        "locale": row["locale"] if "locale" in row.keys() else "en",
        "email_verified": bool(row["email_verified"]) if "email_verified" in row.keys() else True,
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


@bp.route("/api/auth/resend-verification", methods=["POST"])
def auth_resend_verification():
    """Resend email verification link (JSON API)."""
    data = request.get_json(force=True)
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Email is required"}), 400

    from auth import User
    user = User.get_by_email(email)
    if not user:
        # Don't reveal whether the email exists
        return jsonify({"success": True})

    # Already verified — nothing to do
    email_verified = user["email_verified"] if "email_verified" in user.keys() else 1
    if email_verified:
        return jsonify({"success": True, "message": "Email already verified"})

    try:
        token = secrets.token_urlsafe(32)
        db = get_db()
        db.execute(
            "UPDATE users SET email_verification_token = ? WHERE id = ?",
            (token, user["id"]),
        )
        db.commit()

        from flask import current_app
        from email_service import EmailService
        base = current_app.config.get("BASE_URL", "http://localhost:5001")
        verify_url = f"{base}/verify-email/{token}"
        EmailService.send(
            email,
            "Verify Your Email — IB Study Companion",
            f"<p>Here's your verification link:</p>"
            f'<p><a href="{verify_url}">Verify Email Address</a></p>'
            f"<p>This link expires in 24 hours.</p>",
        )
    except Exception as e:
        logger.error("resend_verification failed: %s", e, exc_info=True)

    return jsonify({"success": True})


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
        return jsonify({
            "name": current_user.name,
            "exam_session": "",
            "subjects": [],
            "onboarding_complete": False,
        })

    subjects = []
    for i, s in enumerate(profile.subjects):
        topics = get_syllabus_topics(s.name)
        subjects.append({
            "id": i + 1,
            "name": s.name,
            "level": s.level,
            "topics": [t.name for t in topics] if topics else [],
        })

    return jsonify({
        "name": profile.name,
        "exam_session": profile.exam_session,
        "subjects": subjects,
        "onboarding_complete": True,
    })


@bp.route("/api/gamification/status")
@login_required
def gamification_status():
    """Return gamification data (XP, streak, badges)."""
    uid = current_user_id()
    try:
        gam = GamificationProfileDB(uid)
        activity_log = ActivityLogDB(uid)
        try:
            gam.update_streak(activity_log)
        except Exception:
            db = get_db()
            try:
                db.execute("ROLLBACK")
            except Exception:
                pass
            logging.warning("gamification: update_streak failed for user %s", uid)

        # Compute level from XP (100 XP per level)
        xp_per_level = 100
        level = (gam.total_xp // xp_per_level) + 1
        xp_in_level = gam.total_xp % xp_per_level
        xp_progress_pct = round((xp_in_level / xp_per_level) * 100)

        daily_goal = gam.daily_goal_xp or 50
        daily_goal_pct = min(100, round((gam.daily_xp_today / daily_goal) * 100)) if daily_goal > 0 else 0

        streak_freeze = gam.streak_freeze_available

        return jsonify({
            "level": level,
            "total_xp": gam.total_xp,
            "xp_progress_pct": xp_progress_pct,
            "current_streak": gam.current_streak,
            "streak_freeze_available": streak_freeze,
            "daily_xp_today": gam.daily_xp_today,
            "daily_goal_xp": daily_goal,
            "daily_goal_pct": daily_goal_pct,
        })
    except Exception as exc:
        logging.exception("gamification_status failed for user %s: %s", uid, exc)
        db = get_db()
        try:
            db.execute("ROLLBACK")
        except Exception:
            pass
        return jsonify({
            "level": 1,
            "total_xp": 0,
            "xp_progress_pct": 0,
            "current_streak": 0,
            "streak_freeze_available": 0,
            "daily_xp_today": 0,
            "daily_goal_xp": 50,
            "daily_goal_pct": 0,
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
    avg_grade = 0.0
    entries = grade_log.entries
    if entries:
        avg_grade = round(sum(e.percentage for e in entries) / len(entries), 1)

    # Count upcoming (incomplete) planner tasks
    upcoming_tasks = 0
    try:
        plan_data = StudyPlanDB(uid).load()
        if plan_data:
            for dp in plan_data["daily_plans"]:
                for t in dp.tasks:
                    if not t.completed:
                        upcoming_tasks += 1
    except Exception:
        pass

    stats = {
        "total_questions": total_questions,
        "avg_grade": avg_grade,
        "current_streak": gam.current_streak,
        "upcoming_tasks": upcoming_tasks,
    }

    # Recent activity — matches frontend ActivityItem type
    recent_activity = []
    for idx, e in enumerate(grade_log.recent(10)):
        recent_activity.append({
            "id": idx + 1,
            "type": "study",
            "description": f"{e.subject_display} — {e.command_term}: Grade {e.grade} ({e.percentage}%)",
            "timestamp": e.timestamp,
            "subject": e.subject_display,
        })

    # Progress data (last 30 days) — matches frontend ProgressDataPoint type
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
            "score": round(sum(pcts) / len(pcts)),
            "questions": len(pcts),
        })

    return jsonify({
        "stats": stats,
        "recent_activity": recent_activity,
        "progress": progress,
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
    """Return syllabus topics for a subject as string array."""
    topics = get_syllabus_topics(subject)
    if not topics:
        return jsonify({"topics": []})

    return jsonify({
        "topics": [t.name for t in topics],
    })


# ── Flashcards ───────────────────────────────────────────────

@bp.route("/api/flashcards/decks")
@login_required
def flashcard_decks():
    """Return flashcard decks grouped by subject."""
    uid = current_user_id()
    fc = FlashcardDeckDB(uid)
    today = date.today().isoformat()

    # Group cards by subject into virtual "decks"
    decks_map: dict[str, dict] = {}
    for card in fc.cards:
        subj = card.subject or "General"
        if subj not in decks_map:
            decks_map[subj] = {
                "id": hash(subj) % 1_000_000,
                "name": subj,
                "subject": subj,
                "card_count": 0,
                "due_count": 0,
                "mastered": 0,
                "created_at": "",
            }
        decks_map[subj]["card_count"] += 1
        if card.next_review and card.next_review <= today:
            decks_map[subj]["due_count"] += 1
        # Card is "mastered" if interval >= 21 days
        if hasattr(card, "interval_days") and (card.interval_days or 0) >= 21:
            decks_map[subj]["mastered"] += 1

    decks = []
    for d in decks_map.values():
        card_count = d["card_count"]
        mastery_pct = round((d["mastered"] / card_count) * 100) if card_count > 0 else 0
        decks.append({
            "id": d["id"],
            "name": d["name"],
            "subject": d["subject"],
            "card_count": card_count,
            "due_count": d["due_count"],
            "mastery_pct": mastery_pct,
            "created_at": d["created_at"],
        })

    return jsonify({"decks": decks})


def _serialize_flashcard(c, deck_id_val=0):
    """Serialize a flashcard to match the frontend Flashcard type."""
    interval = getattr(c, "interval_days", 1) or 1
    ease = getattr(c, "ease_factor", 2.5) or 2.5
    # Infer difficulty from interval
    if interval >= 14:
        difficulty = "easy"
    elif interval >= 3:
        difficulty = "medium"
    else:
        difficulty = "hard"
    return {
        "id": c.id,
        "deck_id": deck_id_val,
        "front": c.front,
        "back": c.back,
        "difficulty": difficulty,
        "next_review": c.next_review or "",
        "interval": interval,
        "ease_factor": ease,
    }


@bp.route("/api/flashcards/decks/<deck_id>")
@login_required
def flashcard_deck_detail(deck_id):
    """Return cards in a specific deck (subject)."""
    uid = current_user_id()
    fc = FlashcardDeckDB(uid)
    deck_id_num = hash(deck_id) % 1_000_000

    matching = [c for c in fc.cards if c.subject == deck_id]
    due_count = sum(1 for c in matching if c.next_review and c.next_review <= date.today().isoformat())
    mastered = sum(1 for c in matching if (getattr(c, "interval_days", 0) or 0) >= 21)
    mastery_pct = round((mastered / len(matching)) * 100) if matching else 0

    deck = {
        "id": deck_id_num,
        "name": deck_id,
        "subject": deck_id,
        "card_count": len(matching),
        "due_count": due_count,
        "mastery_pct": mastery_pct,
        "created_at": "",
    }
    cards = [_serialize_flashcard(c, deck_id_num) for c in matching]

    return jsonify({"deck": deck, "cards": cards})


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
            deck_id_num = hash(c.subject or "General") % 1_000_000
            cards.append(_serialize_flashcard(c, deck_id_num))

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
    """Return study plan tasks matching frontend PlannerTask type."""
    uid = current_user_id()
    plan_data = StudyPlanDB(uid).load()

    tasks = []
    task_counter = 1
    if plan_data:
        for dp in plan_data["daily_plans"]:
            for i, t in enumerate(dp.tasks):
                # Build a human-readable title from task data
                title = f"{t.task_type.replace('_', ' ').title()}: {t.subject}"
                if t.topic:
                    title += f" — {t.topic}"
                description = f"{t.duration_minutes} min {t.task_type} session"

                tasks.append({
                    "id": task_counter,
                    "title": title,
                    "description": description,
                    "due_date": dp.date,
                    "completed": t.completed,
                    "subject": t.subject,
                    "priority": t.priority or "medium",
                    "_composite_id": f"{dp.date}_{i}",
                })
                task_counter += 1

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

    # Support numeric ID (sequential counter from task list) or composite "date_index"
    try:
        numeric_id = int(task_id)
        # Walk through tasks in same order as planner_tasks() to find the matching one
        counter = 1
        for dp in plan_data["daily_plans"]:
            for i, t in enumerate(dp.tasks):
                if counter == numeric_id:
                    t.completed = completed
                    plan_db.save(plan_data)
                    return jsonify({"success": True})
                counter += 1
    except ValueError:
        # Fallback: composite "date_index" format
        parts = task_id.rsplit("_", 1)
        if len(parts) == 2:
            target_date, idx_str = parts
            try:
                idx = int(idx_str)
                for dp in plan_data["daily_plans"]:
                    if dp.date == target_date and idx < len(dp.tasks):
                        dp.tasks[idx].completed = completed
                        plan_db.save(plan_data)
                        return jsonify({"success": True})
            except ValueError:
                pass

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
        logger.error("generate_study_plan failed: %s", e, exc_info=True)
        return jsonify({"error": "Something went wrong. Please try again."}), 500


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

@bp.route("/api/account/profile")
@login_required
def get_account_profile():
    """Return user account info for the account settings page."""
    uid = current_user_id()
    db = get_db()
    row = db.execute(
        "SELECT id, name, email, role, created_at, locale FROM users WHERE id = ?",
        (uid,),
    ).fetchone()
    if not row:
        return jsonify({"error": "User not found"}), 404

    profile = StudentProfileDB.load(uid)
    plan = "free"
    credits = 0
    try:
        sub = db.execute(
            "SELECT plan_id FROM user_subscriptions WHERE user_id = ?", (uid,)
        ).fetchone()
        if sub:
            plan = sub["plan_id"] or "free"
        cred = db.execute(
            "SELECT balance FROM credit_balances WHERE user_id = ?", (uid,)
        ).fetchone()
        if cred:
            credits = cred["balance"] or 0
    except Exception:
        try:
            db.execute("ROLLBACK")
        except Exception:
            pass

    return jsonify({
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "role": row["role"] or "student",
        "plan": plan,
        "credits": credits,
        "exam_session": profile.exam_session if profile else "",
        "created_at": row["created_at"] or "",
    })


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
    """Return community papers as paginated CommunityPost items."""
    uid = current_user_id()
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
        paper_id = r["id"]

        # Aggregate votes (sum of ratings)
        vote_row = db.execute(
            "SELECT COALESCE(SUM(rating), 0) as votes FROM paper_ratings WHERE paper_id = ?",
            (paper_id,),
        ).fetchone()
        votes = vote_row["votes"] if vote_row else 0

        # User's own vote
        user_vote_row = db.execute(
            "SELECT rating FROM paper_ratings WHERE paper_id = ? AND user_id = ?",
            (paper_id, uid),
        ).fetchone()
        user_vote = user_vote_row["rating"] if user_vote_row else 0

        # Real comment count
        comment_row = db.execute(
            "SELECT COUNT(*) as cnt FROM community_comments WHERE post_id = ?",
            (paper_id,),
        ).fetchone()
        comment_count = comment_row["cnt"] if comment_row else 0

        items.append({
            "id": paper_id,
            "title": r["title"],
            "content": r.get("description", "") or f"{r['subject']} {r['level']} resource",
            "author": r["author_name"] or "Anonymous",
            "author_id": r["uploader_id"],
            "subject": r["subject"],
            "votes": votes,
            "comment_count": comment_count,
            "created_at": r["created_at"],
            "user_vote": user_vote,
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


@bp.route("/api/community/posts/<int:post_id>/comments")
@login_required
def get_post_comments(post_id):
    """Return comments for a community post."""
    db = get_db()
    rows = db.execute(
        """SELECT c.id, c.content, c.created_at, c.user_id, u.name as author_name
           FROM community_comments c
           JOIN users u ON c.user_id = u.id
           WHERE c.post_id = ?
           ORDER BY c.created_at ASC""",
        (post_id,),
    ).fetchall()
    return jsonify({"comments": [dict(r) for r in rows]})


@bp.route("/api/community/posts/<int:post_id>/comments", methods=["POST"])
@login_required
def create_comment(post_id):
    """Create a comment on a community post."""
    data = request.get_json(force=True)
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "Comment cannot be empty."}), 400

    uid = current_user_id()
    db = get_db()

    # Verify post exists
    post = db.execute(
        "SELECT id FROM community_papers WHERE id = ?", (post_id,)
    ).fetchone()
    if not post:
        return jsonify({"error": "Post not found."}), 404

    db.execute(
        "INSERT INTO community_comments (post_id, user_id, content, created_at) VALUES (?, ?, ?, ?)",
        (post_id, uid, content, datetime.now().isoformat()),
    )
    db.commit()
    return jsonify({"success": True}), 201


# ── Community Moderation ─────────────────────────────────────

@bp.route("/api/community/posts/<int:post_id>/report", methods=["POST"])
@login_required
def report_community_post(post_id):
    """Report a community post for moderation review."""
    uid = current_user_id()
    data = request.get_json(force=True)
    reason = (data.get("reason") or "").strip()

    if not reason:
        return jsonify({"error": "A reason is required."}), 400

    db = get_db()
    # Verify post exists
    post = db.execute("SELECT id FROM community_papers WHERE id = ?", (post_id,)).fetchone()
    if not post:
        return jsonify({"error": "Post not found."}), 404

    # Prevent duplicate reports from the same user
    existing = db.execute(
        "SELECT id FROM paper_reports WHERE paper_id = ? AND reporter_id = ?",
        (post_id, uid),
    ).fetchone()
    if existing:
        return jsonify({"success": True, "message": "Already reported."})

    db.execute(
        "INSERT INTO paper_reports (paper_id, reporter_id, reason, created_at) VALUES (?, ?, ?, ?)",
        (post_id, uid, reason, datetime.now().isoformat()),
    )
    db.commit()
    return jsonify({"success": True, "message": "Report submitted. Thank you for keeping the community safe."})


@bp.route("/api/community/posts/<int:post_id>", methods=["DELETE"])
@login_required
def delete_community_post(post_id):
    """Delete a community post — only the author can delete their own post."""
    uid = current_user_id()
    db = get_db()
    post = db.execute("SELECT id, uploader_id FROM community_papers WHERE id = ?", (post_id,)).fetchone()
    if not post:
        return jsonify({"error": "Post not found."}), 404
    if post["uploader_id"] != uid:
        return jsonify({"error": "You can only delete your own posts."}), 403

    db.execute("DELETE FROM community_comments WHERE post_id = ?", (post_id,))
    db.execute("DELETE FROM paper_ratings WHERE paper_id = ?", (post_id,))
    db.execute("DELETE FROM paper_reports WHERE paper_id = ?", (post_id,))
    db.execute("DELETE FROM community_papers WHERE id = ?", (post_id,))
    db.commit()
    return jsonify({"success": True})


# ── Analytics Events ──────────────────────────────────────────

@bp.route("/api/analytics/event", methods=["POST"])
def analytics_event():
    """Ingest frontend analytics event (fire-and-forget)."""
    analytics_logger = logging.getLogger("analytics")
    try:
        data = request.get_json(silent=True) or {}
        uid = current_user.id if current_user.is_authenticated else None
        event_type = data.get("type", "unknown")
        analytics_logger.info(
            "analytics %s user=%s event=%s path=%s",
            event_type,
            uid,
            data.get("event", ""),
            data.get("path", ""),
        )
    except Exception:
        pass
    return jsonify({"ok": True})


# ── Groups ───────────────────────────────────────────────────

@bp.route("/api/groups")
@login_required
def list_groups():
    """Return study groups matching frontend StudyGroup type."""
    uid = current_user_id()
    db = get_db()
    rows = db.execute(
        "SELECT g.*, "
        "(SELECT COUNT(*) FROM group_members gm WHERE gm.group_id = g.id) as member_count, "
        "(SELECT 1 FROM group_members gm WHERE gm.group_id = g.id AND gm.user_id = ?) as is_member, "
        "(SELECT 1 FROM group_members gm WHERE gm.group_id = g.id AND gm.user_id = ? AND gm.role = 'admin') as is_admin "
        "FROM study_groups g ORDER BY g.created_at DESC",
        (uid, uid),
    ).fetchall()

    groups = []
    for r in rows:
        groups.append({
            "id": r["id"],
            "name": r["name"],
            "description": r.get("description", "") or "",
            "member_count": r["member_count"] or 0,
            "subject": r["subject"] or "",
            "is_member": bool(r["is_member"]),
            "is_admin": bool(r["is_admin"]),
        })

    return jsonify({"groups": groups})


@bp.route("/api/groups/<int:group_id>/join", methods=["POST"])
@login_required
def join_group(group_id):
    """Join a study group."""
    uid = current_user_id()
    db = get_db()

    existing = db.execute(
        "SELECT 1 FROM group_members WHERE group_id = ? AND user_id = ?",
        (group_id, uid),
    ).fetchone()
    if existing:
        return jsonify({"success": True})

    db.execute(
        "INSERT INTO group_members (group_id, user_id, role, joined_at) VALUES (?, ?, 'member', ?)",
        (group_id, uid, datetime.now().isoformat()),
    )
    db.commit()
    return jsonify({"success": True})


@bp.route("/api/groups/<int:group_id>/leave", methods=["POST"])
@login_required
def leave_group(group_id):
    """Leave a study group."""
    uid = current_user_id()
    db = get_db()

    membership = db.execute(
        "SELECT role FROM group_members WHERE group_id = ? AND user_id = ?",
        (group_id, uid),
    ).fetchone()
    if not membership:
        return jsonify({"error": "Not a member of this group."}), 400

    db.execute(
        "DELETE FROM group_members WHERE group_id = ? AND user_id = ?",
        (group_id, uid),
    )
    db.commit()
    return jsonify({"success": True})


@bp.route("/api/groups/<int:group_id>", methods=["DELETE"])
@login_required
def delete_group(group_id):
    """Delete a study group — only the creator (admin) can delete."""
    uid = current_user_id()
    db = get_db()

    membership = db.execute(
        "SELECT role FROM group_members WHERE group_id = ? AND user_id = ?",
        (group_id, uid),
    ).fetchone()
    if not membership or membership["role"] != "admin":
        return jsonify({"error": "Only the group creator can delete this group."}), 403

    db.execute("DELETE FROM group_members WHERE group_id = ?", (group_id,))
    db.execute("DELETE FROM study_groups WHERE id = ?", (group_id,))
    db.commit()
    return jsonify({"success": True})


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


# ── Flashcard generation from documents ──────────────────────

@bp.route("/api/flashcards/generate", methods=["POST"])
@login_required
def generate_flashcards_from_doc():
    """Generate flashcards from a specific uploaded document using AI.

    Accepts { document_id: int, count: int (default 10) }.
    Retrieves document chunks, sends them to the engine, and creates cards.
    """
    uid = current_user_id()
    data = request.get_json(silent=True) or {}
    doc_id = data.get("document_id")
    count = min(int(data.get("count", 10)), 30)

    if not doc_id:
        return jsonify({"error": "document_id is required."}), 400

    db = get_db()

    # Get document metadata
    doc = db.execute(
        "SELECT id, filename, subject, doc_type FROM uploads WHERE id = ? AND user_id = ?",
        (doc_id, uid),
    ).fetchone()
    if not doc:
        return jsonify({"error": "Document not found."}), 404

    subject = doc["subject"] or "General"

    # Retrieve stored text chunks for this document
    chunks = db.execute(
        "SELECT content FROM document_chunks WHERE upload_id = ? ORDER BY chunk_index LIMIT 20",
        (doc_id,),
    ).fetchall()

    if not chunks:
        # Fallback: try ChromaDB
        try:
            from vector_store import get_vector_store
            vs = get_vector_store()
            results = vs.query(
                query_text=f"{subject} key concepts",
                n_results=15,
                where={"source": doc["filename"]},
            )
            if results and results.get("documents"):
                chunk_texts = results["documents"][0] if isinstance(results["documents"][0], list) else results["documents"]
            else:
                return jsonify({"error": "No text extracted from this document. Try re-uploading."}), 400
        except Exception:
            return jsonify({"error": "No text extracted from this document. Try re-uploading."}), 400
    else:
        chunk_texts = [c["content"] for c in chunks]

    # Combine chunks into context (limit ~8k chars)
    context = "\n\n---\n\n".join(chunk_texts)[:8000]

    try:
        engine = EngineManager.get_engine()
        cards_raw = engine.generate_flashcards(
            context=context,
            subject=subject,
            count=count,
        )
    except AttributeError:
        # Engine doesn't have generate_flashcards — use a simple prompt-based approach
        try:
            from ai_core import call_llm
            prompt = (
                f"You are an IB {subject} expert. Based on the following study material, "
                f"create exactly {count} flashcards as JSON. Each flashcard should have "
                f"'front' (a clear question) and 'back' (a concise, accurate answer). "
                f"Focus on key concepts, definitions, and exam-relevant material.\n\n"
                f"Study material:\n{context}\n\n"
                f"Return ONLY valid JSON: [{{'front': '...', 'back': '...'}}]"
            )
            import json
            raw = call_llm(prompt, max_tokens=2000)
            # Parse the JSON from the response
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start >= 0 and end > start:
                cards_raw = json.loads(raw[start:end])
            else:
                cards_raw = []
        except Exception as e:
            logger.error("Flashcard generation failed: %s", e, exc_info=True)
            return jsonify({"error": "Failed to generate flashcards. Please try again."}), 500
    except Exception as e:
        logger.error("Flashcard generation failed: %s", e, exc_info=True)
        return jsonify({"error": "Failed to generate flashcards. Please try again."}), 500

    # Persist generated cards
    fc = FlashcardDeckDB(uid)
    created = []
    for card in cards_raw[:count]:
        front = card.get("front", "").strip()
        back = card.get("back", "").strip()
        if front and back:
            new_card = fc.add_card(front=front, back=back, subject=subject)
            if new_card:
                created.append({"id": new_card.id, "front": front, "back": back})

    return jsonify({
        "success": True,
        "cards_created": len(created),
        "subject": subject,
        "cards": created,
    })
