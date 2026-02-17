"""
Application configuration — environment-aware settings.

All environment variables are documented here. See .env.example for a template.
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path

BASE_DIR = Path(__file__).parent


# ---------------------------------------------------------------------------
# Feature flags — simple dict, no external service
# ---------------------------------------------------------------------------
FEATURE_FLAGS: dict[str, bool] = {
    "oral_practice": True,
    "examiner_reviews": False,
    "stripe_payments": True,
}


class BaseConfig:
    # Core Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-in-production")
    # Database: SQLite (default) or PostgreSQL (set DATABASE_URL=postgresql://...)
    DATABASE = os.environ.get("DATABASE_URL", str(BASE_DIR / "ib_study.db"))
    WTF_CSRF_ENABLED = True

    # Session security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 86400

    # Upload limits
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # AI provider keys
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

    # Web push (VAPID)
    VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
    VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
    VAPID_CLAIMS_EMAIL = os.environ.get("VAPID_CLAIMS_EMAIL", "mailto:admin@example.com")

    # Logging
    LOG_FORMAT = os.environ.get("LOG_FORMAT", "text")  # "json" or "text"
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    # Email
    EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "log")  # "log" or "smtp"
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_FROM = os.environ.get("MAIL_FROM", "noreply@example.com")
    BASE_URL = os.environ.get("BASE_URL", "http://localhost:5001")

    # Redis / Sentry
    REDIS_URL = os.environ.get("REDIS_URL", "")
    SENTRY_DSN = os.environ.get("SENTRY_DSN", "")

    # Stripe payments
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
    STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

    # Google OAuth
    GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
    GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")

    # Response compression
    COMPRESS_MIMETYPES = [
        "text/html", "text/css", "text/xml", "text/javascript",
        "application/json", "application/javascript", "application/xml",
    ]
    COMPRESS_MIN_SIZE = 500

    # Rate limiting (defaults to in-memory; set REDIS_URL for Redis-backed)
    RATELIMIT_STORAGE_URI = os.environ.get("REDIS_URL", "") or "memory://"

    # Server-side sessions (defaults to filesystem; upgraded to Redis when available)
    SESSION_TYPE = "filesystem"
    SESSION_PERMANENT = True
    SESSION_KEY_PREFIX = "ibstudy:"

    FEATURE_FLAGS = FEATURE_FLAGS


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    LOG_FORMAT = os.environ.get("LOG_FORMAT", "text")


class ProductionConfig(BaseConfig):
    DEBUG = False
    LOG_FORMAT = os.environ.get("LOG_FORMAT", "json")
    SESSION_COOKIE_SECURE = True

    @classmethod
    def validate(cls):
        """Fail fast on missing or insecure configuration in production."""
        errors: list[str] = []

        if cls.SECRET_KEY in ("dev-key-change-in-production", ""):
            errors.append("SECRET_KEY must be set to a secure value in production.")

        if not cls.GOOGLE_API_KEY:
            warnings.warn("GOOGLE_API_KEY is not set — AI features will be unavailable.")

        if errors:
            raise RuntimeError(
                "Production configuration errors:\n" + "\n".join(f"  - {e}" for e in errors)
            )


class TestingConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
