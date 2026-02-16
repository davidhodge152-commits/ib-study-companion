"""
Application configuration — environment-aware settings.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).parent


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-in-production")
    DATABASE = os.environ.get("DATABASE_URL", str(BASE_DIR / "ib_study.db"))
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
    WTF_CSRF_ENABLED = True


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False


class TestingConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
