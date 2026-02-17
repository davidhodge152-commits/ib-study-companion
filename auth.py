"""
User Authentication — Flask-Login blueprint.

Provides register, login, and logout routes.
Uses werkzeug.security for password hashing.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, redirect, render_template, request, url_for, flash
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_db
from extensions import limiter
from audit import log_event

LOCKOUT_THRESHOLD = 5
LOCKOUT_MINUTES = 15

auth_bp = Blueprint("auth", __name__)
login_manager = LoginManager()
login_manager.login_view = "auth.login"


class User(UserMixin):
    """Wraps a DB user row for Flask-Login."""

    def __init__(self, id: int, name: str, email: str, role: str = "student"):
        self.id = id
        self.name = name
        self.email = email
        self.role = role

    @property
    def is_teacher(self):
        return self.role == "teacher"

    @property
    def is_admin(self):
        return self.role == "admin"

    @staticmethod
    def get(user_id: int):
        db = get_db()
        row = db.execute("SELECT id, name, email, role FROM users WHERE id = ?", (user_id,)).fetchone()
        if row:
            return User(row["id"], row["name"], row["email"], row["role"] if "role" in row.keys() else "student")
        return None

    @staticmethod
    def get_by_email(email: str):
        db = get_db()
        row = db.execute(
            "SELECT id, name, email, password_hash, role, login_attempts, locked_until "
            "FROM users WHERE email = ?", (email,),
        ).fetchone()
        if row:
            return row
        return None


@login_manager.user_loader
def load_user(user_id):
    return User.get(int(user_id))


def _validate_password(password: str) -> str | None:
    """Return an error message if password is too weak, else None."""
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if not any(c.isupper() for c in password):
        return "Password must contain at least one uppercase letter."
    if not any(c.islower() for c in password):
        return "Password must contain at least one lowercase letter."
    if not any(c.isdigit() for c in password):
        return "Password must contain at least one digit."
    return None


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per 15 minutes", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("core.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            return render_template("login.html", error="Email and password are required.")

        row = User.get_by_email(email)
        if not row:
            return render_template("login.html", error="Invalid email or password.")

        # Check account lockout
        locked_until = row["locked_until"] if "locked_until" in row.keys() else ""
        if locked_until:
            try:
                lock_time = datetime.fromisoformat(locked_until)
                remaining = (lock_time - datetime.now()).total_seconds()
                if remaining > 0:
                    mins = math.ceil(remaining / 60)
                    log_event("login_locked", row["id"], f"email={email}")
                    return render_template(
                        "login.html",
                        error=f"Account temporarily locked. Try again in {mins} minute(s).",
                    )
            except (ValueError, TypeError):
                pass

        if not row["password_hash"] or not check_password_hash(row["password_hash"], password):
            # Increment login attempts
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
            return render_template("login.html", error="Invalid email or password.")

        # Success — reset lockout fields
        db = get_db()
        db.execute("UPDATE users SET login_attempts=0, locked_until='' WHERE id=?", (row["id"],))
        db.commit()

        role = row["role"] if "role" in row.keys() else "student"
        user = User(row["id"], row["name"], row["email"], role)
        login_user(user, remember=True)
        log_event("login_success", row["id"])
        next_page = request.args.get("next")
        return redirect(next_page or url_for("core.dashboard"))

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("3 per hour", methods=["POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("core.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not name or not email or not password:
            return render_template("register.html", error="All fields are required.")

        if password != confirm:
            return render_template("register.html", error="Passwords do not match.")

        pw_error = _validate_password(password)
        if pw_error:
            return render_template("register.html", error=pw_error)

        existing = User.get_by_email(email)
        if existing:
            return render_template("register.html", error="An account with this email already exists.")

        db = get_db()
        cur = db.execute(
            "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (name, email, generate_password_hash(password), datetime.now().isoformat()),
        )
        user_id = cur.lastrowid
        # Create gamification row
        db.execute("INSERT OR IGNORE INTO gamification (user_id) VALUES (?)", (user_id,))
        db.commit()

        log_event("register", user_id, f"email={email}")
        user = User(user_id, name, email)
        login_user(user, remember=True)
        return redirect(url_for("core.onboarding"))

    return render_template("register.html")


@auth_bp.route("/register/teacher", methods=["GET", "POST"])
@limiter.limit("3 per hour", methods=["POST"])
def register_teacher():
    if current_user.is_authenticated:
        return redirect(url_for("core.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        school_code = request.form.get("school_code", "").strip()

        if not name or not email or not password or not school_code:
            return render_template("register_teacher.html", error="All fields are required.")

        if password != confirm:
            return render_template("register_teacher.html", error="Passwords do not match.")

        pw_error = _validate_password(password)
        if pw_error:
            return render_template("register_teacher.html", error=pw_error)

        # Validate school code
        db = get_db()
        school = db.execute("SELECT id FROM schools WHERE code = ?", (school_code,)).fetchone()
        if not school:
            return render_template("register_teacher.html", error="Invalid school code.")

        existing = User.get_by_email(email)
        if existing:
            return render_template("register_teacher.html", error="An account with this email already exists.")

        cur = db.execute(
            "INSERT INTO users (name, email, password_hash, role, school_id, created_at) VALUES (?, ?, ?, 'teacher', ?, ?)",
            (name, email, generate_password_hash(password), school["id"], datetime.now().isoformat()),
        )
        user_id = cur.lastrowid
        db.execute("INSERT OR IGNORE INTO gamification (user_id) VALUES (?)", (user_id,))
        db.commit()

        log_event("register_teacher", user_id, f"email={email} school={school_code}")
        user = User(user_id, name, email, "teacher")
        login_user(user, remember=True)
        return redirect(url_for("teacher.teacher_dashboard"))

    return render_template("register_teacher.html")


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("3 per hour", methods=["POST"])
def forgot_password():
    if request.method == "POST":
        import secrets
        email = request.form.get("email", "").strip().lower()
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
            reset_url = f"{base}/reset-password/{row['id']}/{token}"
            EmailService.send(
                email,
                "Password Reset — IB Study Companion",
                f"<p>Click the link below to reset your password (expires in 1 hour):</p>"
                f'<p><a href="{reset_url}">{reset_url}</a></p>'
                f"<p>If you did not request this, ignore this email.</p>",
            )
            log_event("password_reset_request", row["id"])

        return render_template("forgot_password.html",
                               message="If an account exists with that email, a reset link has been sent.")

    return render_template("forgot_password.html")


@auth_bp.route("/reset-password/<int:user_id>/<token>", methods=["GET", "POST"])
def reset_password(user_id, token):
    db = get_db()
    row = db.execute(
        "SELECT id, reset_token, reset_token_expires FROM users WHERE id=?",
        (user_id,),
    ).fetchone()

    if not row or not row["reset_token"]:
        return render_template("reset_password.html", error="Invalid or expired reset link.", invalid=True)

    # Verify token hash
    if not check_password_hash(row["reset_token"], token):
        return render_template("reset_password.html", error="Invalid or expired reset link.", invalid=True)

    # Check expiry
    try:
        expires = datetime.fromisoformat(row["reset_token_expires"])
        if datetime.now() > expires:
            return render_template("reset_password.html", error="This reset link has expired.", invalid=True)
    except (ValueError, TypeError):
        return render_template("reset_password.html", error="Invalid or expired reset link.", invalid=True)

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if password != confirm:
            return render_template("reset_password.html", error="Passwords do not match.")

        pw_error = _validate_password(password)
        if pw_error:
            return render_template("reset_password.html", error=pw_error)

        db.execute(
            "UPDATE users SET password_hash=?, reset_token='', reset_token_expires='', "
            "login_attempts=0, locked_until='' WHERE id=?",
            (generate_password_hash(password), user_id),
        )
        db.commit()
        log_event("password_reset_complete", user_id)
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html")


@auth_bp.route("/api/account/export")
@login_required
def account_export():
    """GDPR: Export all user data as JSON."""
    from flask_login import current_user
    import json as json_mod
    uid = current_user.id
    db = get_db()

    user_row = db.execute("SELECT id, name, email, role, exam_session, created_at FROM users WHERE id=?", (uid,)).fetchone()
    subjects = [dict(r) for r in db.execute("SELECT name, level, target_grade FROM user_subjects WHERE user_id=?", (uid,)).fetchall()]
    grades = [dict(r) for r in db.execute("SELECT * FROM grades WHERE user_id=?", (uid,)).fetchall()]
    activity = [dict(r) for r in db.execute("SELECT * FROM activity_log WHERE user_id=?", (uid,)).fetchall()]
    flashcards = [dict(r) for r in db.execute("SELECT * FROM flashcards WHERE user_id=?", (uid,)).fetchall()]

    data = {
        "user": dict(user_row) if user_row else {},
        "subjects": subjects,
        "grades": grades,
        "activity_log": activity,
        "flashcards": flashcards,
        "exported_at": datetime.now().isoformat(),
    }
    log_event("data_export", uid, "type=gdpr_account_export")
    return jsonify(data)


@auth_bp.route("/api/account/delete", methods=["POST"])
@login_required
def account_delete():
    """GDPR: Delete user account after password confirmation."""
    from flask_login import current_user
    uid = current_user.id
    password = request.form.get("password", "")

    if not password:
        return jsonify({"error": "Password is required to confirm account deletion."}), 400

    db = get_db()
    row = db.execute("SELECT password_hash FROM users WHERE id=?", (uid,)).fetchone()
    if not row or not check_password_hash(row["password_hash"], password):
        return jsonify({"error": "Incorrect password."}), 403

    log_event("account_delete", uid)
    db.execute("DELETE FROM users WHERE id=?", (uid,))
    db.commit()
    logout_user()
    return jsonify({"success": True, "message": "Account deleted."})


@auth_bp.route("/logout")
def logout():
    uid = current_user.id if current_user.is_authenticated else None
    log_event("logout", uid)
    logout_user()
    return redirect(url_for("auth.login"))
