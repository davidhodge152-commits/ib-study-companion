"""
IB Study Companion — Flask Web Application

Target-driven study platform with IB lifecycle management, parent portal,
spaced repetition, and study planner.
"""

from __future__ import annotations

import hashlib
import os
from typing import Any

from flask import Flask, Response, request as flask_request

import database
from auth import auth_bp, login_manager
from blueprints import register_blueprints
from extensions import limiter


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)

    # Load config
    if test_config is not None:
        app.config.update(test_config)
    else:
        from config import config_by_name
        env = os.environ.get("FLASK_ENV", "development")
        cfg = config_by_name.get(env, config_by_name["development"])
        app.config.from_object(cfg)
        if hasattr(cfg, "validate"):
            cfg.validate()

    app.secret_key = app.config.get("SECRET_KEY", os.environ.get('SECRET_KEY', 'dev-key-change-in-production'))

    # CSRF protection
    try:
        from flask_wtf.csrf import CSRFProtect
        csrf = CSRFProtect(app)
        app.extensions["csrf"] = csrf
    except ImportError:
        csrf = None

    # Ensure csrf_token() is always available in templates (even when CSRF is disabled in tests)
    if "csrf_token" not in app.jinja_env.globals:
        app.jinja_env.globals["csrf_token"] = lambda: ""

    # Server-side sessions (Redis if REDIS_URL set, filesystem fallback)
    # On Vercel, use Flask's default signed-cookie sessions (no filesystem)
    if not app.config.get("TESTING") and not os.environ.get("VERCEL"):
        try:
            from flask_session import Session
            if "SESSION_TYPE" not in app.config:
                app.config["SESSION_TYPE"] = "filesystem"
            redis_url = app.config.get("REDIS_URL", "")
            if redis_url:
                try:
                    import redis
                    app.config["SESSION_TYPE"] = "redis"
                    app.config["SESSION_REDIS"] = redis.Redis.from_url(redis_url)
                except (ImportError, Exception):
                    app.config["SESSION_TYPE"] = "filesystem"
            Session(app)
        except ImportError:
            pass

    # i18n with Flask-Babel
    try:
        from flask_babel import Babel
        from flask_login import current_user
        from flask import request
        babel = Babel()

        def get_locale():
            if current_user.is_authenticated:
                try:
                    from database import get_db
                    db = get_db()
                    row = db.execute("SELECT locale FROM users WHERE id = ?",
                                     (current_user.id,)).fetchone()
                    if row and row["locale"]:
                        return row["locale"]
                except Exception:
                    pass
            return request.accept_languages.best_match(["en", "fr", "es"], default="en")

        babel.init_app(app, locale_selector=get_locale)
    except ImportError:
        pass

    # Response compression (optional dependency)
    try:
        from flask_compress import Compress
        Compress(app)
    except ImportError:
        pass

    # Static file serving for production (whitenoise) with long cache headers
    # On Vercel, static files are served by the CDN — skip WhiteNoise to reduce cold start
    if not os.environ.get("VERCEL"):
        try:
            from whitenoise import WhiteNoise
            app.wsgi_app = WhiteNoise(
                app.wsgi_app,
                root=os.path.join(app.root_path, 'static'),
                prefix='static/',
                max_age=31536000 if not app.debug else 0,
            )
        except ImportError:
            pass

    # Cache backend (Redis or in-memory fallback)
    from cache_backend import init_cache
    init_cache(app)

    # Background task processing (RQ or synchronous fallback)
    from tasks import init_tasks
    init_tasks(app)

    # Structured logging
    from logging_config import init_logging
    init_logging(app)

    # Register database teardown
    database.init_app(app)

    # Rate limiter (disabled in testing)
    limiter.init_app(app)
    if app.config.get("TESTING"):
        limiter.enabled = False

    # Register auth blueprint and login manager
    app.register_blueprint(auth_bp)
    login_manager.init_app(app)

    # Register all application blueprints
    register_blueprints(app)

    # Google OAuth (optional)
    try:
        from oauth import oauth_bp, init_oauth
        init_oauth(app)
        app.register_blueprint(oauth_bp)
    except ImportError:
        pass

    # Asset URL context processor (JS bundling support)
    _manifest_cache: dict = {}

    @app.context_processor
    def asset_helpers() -> dict[str, Any]:
        def asset_url(filename: str) -> str:
            """Map source filename to hashed bundle, falling back to source in dev."""
            if not _manifest_cache:
                manifest_path = os.path.join(app.root_path, "static", "dist", "manifest.json")
                try:
                    import json
                    with open(manifest_path) as f:
                        _manifest_cache.update(json.load(f))
                except (FileNotFoundError, ValueError):
                    pass  # No manifest = dev mode, serve unbundled
            hashed = _manifest_cache.get(filename)
            if hashed:
                return f"/static/dist/{hashed}"
            return f"/static/js/{filename}"
        return {"asset_url": asset_url}

    @app.context_processor
    def oauth_helpers() -> dict[str, Any]:
        try:
            from oauth import is_oauth_available
            return {"google_oauth_available": is_oauth_available()}
        except ImportError:
            return {"google_oauth_available": False}

    # Security headers
    @app.after_request
    def set_security_headers(response: Response) -> Response:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com https://fonts.cdnfonts.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        )
        if not app.debug:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # ETag support for JSON API responses
    @app.after_request
    def set_etag(response: Response) -> Response:
        if (
            response.status_code == 200
            and response.content_type
            and "application/json" in response.content_type
            and response.content_length
            and response.content_length < 1_048_576  # < 1 MB
        ):
            data = response.get_data()
            etag = '"' + hashlib.md5(data).hexdigest() + '"'
            response.headers["ETag"] = etag
            if_none_match = flask_request.headers.get("If-None-Match")
            if if_none_match and if_none_match == etag:
                response.status_code = 304
                response.set_data(b"")
        return response

    # Start centralized scheduler (push reminders, analytics, cache cleanup)
    # On Vercel, cron jobs are handled via HTTP endpoints (see vercel.json)
    if not app.config.get("TESTING") and not os.environ.get("VERCEL"):
        try:
            from scheduler import init_scheduler
            init_scheduler(app)
        except Exception:
            pass

    return app


if __name__ == "__main__":
    create_app().run(debug=True, port=5001)
