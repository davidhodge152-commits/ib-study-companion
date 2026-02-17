"""
User Authentication — Flask-Login blueprint.

Provides register, login, and logout routes.
Uses werkzeug.security for password hashing.
"""

from __future__ import annotations

from flask import Blueprint, redirect, render_template, request, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_db

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
        row = db.execute("SELECT id, name, email, password_hash, role FROM users WHERE email = ?", (email,)).fetchone()
        if row:
            return row
        return None


@login_manager.user_loader
def load_user(user_id):
    return User.get(int(user_id))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("core.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            return render_template("login.html", error="Email and password are required.")

        row = User.get_by_email(email)
        if not row or not row["password_hash"] or not check_password_hash(row["password_hash"], password):
            return render_template("login.html", error="Invalid email or password.")

        role = row["role"] if "role" in row.keys() else "student"
        user = User(row["id"], row["name"], row["email"], role)
        login_user(user, remember=True)
        next_page = request.args.get("next")
        return redirect(next_page or url_for("core.dashboard"))

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
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

        if len(password) < 6:
            return render_template("register.html", error="Password must be at least 6 characters.")

        existing = User.get_by_email(email)
        if existing:
            return render_template("register.html", error="An account with this email already exists.")

        db = get_db()
        from datetime import datetime
        cur = db.execute(
            "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (name, email, generate_password_hash(password), datetime.now().isoformat()),
        )
        user_id = cur.lastrowid
        # Create gamification row
        db.execute("INSERT OR IGNORE INTO gamification (user_id) VALUES (?)", (user_id,))
        db.commit()

        user = User(user_id, name, email)
        login_user(user, remember=True)
        return redirect(url_for("core.onboarding"))

    return render_template("register.html")


@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
