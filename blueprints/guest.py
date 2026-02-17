"""Guest / try-before-signup routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, redirect, render_template, request, session as flask_session, url_for
from flask_login import current_user

bp = Blueprint("guest", __name__)


@bp.route("/try")
def try_page():
    flask_session["guest"] = True
    flask_session["guest_questions"] = 0
    return render_template("try.html", show_sidebar=False)


@bp.before_app_request
def _guest_middleware():
    """Limit guest users to 3 questions and block non-study routes."""
    if flask_session.get("guest") and not current_user.is_authenticated:
        allowed = ["/try", "/static", "/login", "/register", "/api/study/generate",
                   "/api/study/grade", "/study", "/sw.js", "/analytics",
                   "/api/analytics", "/api/push/vapid-key", "/community-analytics"]

        # Enforce 3-question limit on study API calls
        if request.path in ("/api/study/generate", "/api/study/grade"):
            used = flask_session.get("guest_questions", 0)
            if used >= 3:
                return jsonify({
                    "error": "You've used all 3 free questions. Sign up to continue!",
                    "guest_limit": True,
                    "used": used,
                    "limit": 3,
                }), 403

        if not any(request.path.startswith(p) for p in allowed):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Sign up for full access", "guest_limit": True}), 403
            return redirect(url_for("guest.try_page"))
