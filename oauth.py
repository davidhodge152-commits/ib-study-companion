"""Google OAuth integration — optional login via Google."""

from __future__ import annotations

import logging
from datetime import datetime

from flask import Blueprint, redirect, url_for, flash, current_app, session
from flask_login import login_user

from database import get_db
from auth import User
from audit import log_event

logger = logging.getLogger(__name__)

oauth_bp = Blueprint("oauth", __name__)

_oauth_registry = None


def _get_oauth():
    """Lazy-init the OAuth registry."""
    global _oauth_registry
    if _oauth_registry is not None:
        return _oauth_registry

    try:
        from authlib.integrations.flask_client import OAuth
    except ImportError:
        logger.warning("authlib not installed — Google OAuth disabled")
        return None

    _oauth_registry = OAuth()
    return _oauth_registry


def init_oauth(app):
    """Initialize OAuth with the Flask app. Call from create_app()."""
    client_id = app.config.get("GOOGLE_OAUTH_CLIENT_ID", "")
    if not client_id:
        logger.info("GOOGLE_OAUTH_CLIENT_ID not set — Google OAuth disabled")
        return

    oauth = _get_oauth()
    if oauth is None:
        return

    oauth.init_app(app)
    oauth.register(
        name="google",
        client_id=client_id,
        client_secret=app.config.get("GOOGLE_OAUTH_CLIENT_SECRET", ""),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


def is_oauth_available() -> bool:
    """Check if Google OAuth is configured."""
    client_id = current_app.config.get("GOOGLE_OAUTH_CLIENT_ID", "")
    return bool(client_id) and _oauth_registry is not None


@oauth_bp.route("/login/google")
def google_login():
    """Redirect to Google OAuth consent screen."""
    if not is_oauth_available():
        flash("Google login is not configured.", "error")
        return redirect(url_for("auth.login"))

    oauth = _get_oauth()
    redirect_uri = url_for("oauth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@oauth_bp.route("/callback/google")
def google_callback():
    """Handle Google OAuth callback."""
    if not is_oauth_available():
        flash("Google login is not configured.", "error")
        return redirect(url_for("auth.login"))

    oauth = _get_oauth()
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get("userinfo")
        if not user_info:
            user_info = oauth.google.userinfo()
    except Exception as e:
        logger.error("Google OAuth error: %s", e)
        flash("Google login failed. Please try again.", "error")
        return redirect(url_for("auth.login"))

    google_id = user_info.get("sub", "")
    email = user_info.get("email", "").lower()
    name = user_info.get("name", email.split("@")[0])

    if not email:
        flash("Could not get email from Google. Please try again.", "error")
        return redirect(url_for("auth.login"))

    db = get_db()

    # Check if user exists by OAuth ID
    row = db.execute(
        "SELECT id, name, email, role FROM users WHERE oauth_provider = 'google' AND oauth_id = ?",
        (google_id,),
    ).fetchone()

    if row:
        # Existing OAuth user — log in
        user = User(row["id"], row["name"], row["email"], row["role"])
        login_user(user, remember=True)
        log_event("login_google", row["id"])
        return redirect(url_for("core.dashboard"))

    # Check if user exists by email (link accounts)
    row = db.execute(
        "SELECT id, name, email, role FROM users WHERE email = ?",
        (email,),
    ).fetchone()

    if row:
        # Link Google to existing account
        db.execute(
            "UPDATE users SET oauth_provider = 'google', oauth_id = ?, email_verified = 1 WHERE id = ?",
            (google_id, row["id"]),
        )
        db.commit()
        user = User(row["id"], row["name"], row["email"], row["role"])
        login_user(user, remember=True)
        log_event("login_google_linked", row["id"])
        return redirect(url_for("core.dashboard"))

    # New user — create account (auto-verified since Google verified their email)
    cur = db.execute(
        "INSERT INTO users (name, email, password_hash, oauth_provider, oauth_id, email_verified, created_at) "
        "VALUES (?, ?, '', 'google', ?, 1, ?)",
        (name, email, google_id, datetime.now().isoformat()),
    )
    user_id = cur.lastrowid
    db.execute("INSERT OR IGNORE INTO gamification (user_id) VALUES (?)", (user_id,))
    db.commit()

    log_event("register_google", user_id, f"email={email}")
    user = User(user_id, name, email)
    login_user(user, remember=True)
    return redirect(url_for("core.onboarding"))
