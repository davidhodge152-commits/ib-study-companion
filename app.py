"""
IB Study Companion — Flask Web Application

Target-driven study platform with IB lifecycle management, parent portal,
spaced repetition, and study planner.
"""

from __future__ import annotations

import os

from flask import Flask

import database
from auth import auth_bp, login_manager
from blueprints import register_blueprints


def create_app(test_config=None):
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
    except ImportError:
        csrf = None

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

    # Static file serving for production (whitenoise)
    try:
        from whitenoise import WhiteNoise
        app.wsgi_app = WhiteNoise(app.wsgi_app, root=os.path.join(app.root_path, 'static'), prefix='static/')
    except ImportError:
        pass

    # Structured logging
    from logging_config import init_logging
    init_logging(app)

    # Register database teardown
    database.init_app(app)

    # Register auth blueprint and login manager
    app.register_blueprint(auth_bp)
    login_manager.init_app(app)

    # Register all application blueprints
    register_blueprints(app)

    # Start push notification scheduler (non-blocking)
    if not app.config.get("TESTING"):
        try:
            from push import init_scheduler
            init_scheduler(app)
        except Exception:
            pass

    return app


if __name__ == "__main__":
    create_app().run(debug=True, port=5001)
