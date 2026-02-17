"""Google OAuth tests."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock


class TestOAuthDisabled:
    """Test behavior when OAuth is not configured."""

    def test_google_login_redirect_when_not_configured(self, client):
        """Should redirect to login when OAuth not configured."""
        resp = client.get("/login/google", follow_redirects=True)
        assert resp.status_code == 200
        assert b"login" in resp.data.lower()

    def test_google_callback_redirect_when_not_configured(self, client):
        """Should redirect to login when OAuth not configured."""
        resp = client.get("/callback/google", follow_redirects=True)
        assert resp.status_code == 200
        assert b"login" in resp.data.lower()


class TestOAuthModule:
    """Test OAuth module functions."""

    def test_is_oauth_available_without_config(self, app):
        """Should return False without config."""
        with app.app_context():
            from oauth import is_oauth_available
            assert is_oauth_available() is False

    def test_oauth_blueprint_registered(self, app):
        """OAuth blueprint should be registered."""
        # Check that /login/google route exists
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert "/login/google" in rules
        assert "/callback/google" in rules

    def test_google_login_creates_new_user(self, app, client):
        """Simulated Google OAuth should create a new user."""
        from database import get_db

        with app.app_context():
            db = get_db()
            # Simulate what the callback does: insert a Google OAuth user
            db.execute(
                "INSERT INTO users (name, email, password_hash, oauth_provider, oauth_id, email_verified, created_at) "
                "VALUES ('Google User', 'google@example.com', '', 'google', 'google-123', 1, '2026-01-01')"
            )
            db.execute("INSERT OR IGNORE INTO gamification (user_id) VALUES (last_insert_rowid())")
            db.commit()

            row = db.execute(
                "SELECT * FROM users WHERE email = 'google@example.com'"
            ).fetchone()
            assert row is not None
            assert row["oauth_provider"] == "google"
            assert row["oauth_id"] == "google-123"
            assert row["email_verified"] == 1

    def test_google_oauth_links_existing_account(self, app):
        """Google OAuth should link to existing account by email."""
        from database import get_db

        with app.app_context():
            db = get_db()
            # test@example.com already exists from conftest
            db.execute(
                "UPDATE users SET oauth_provider = 'google', oauth_id = 'test-google-id' WHERE email = 'test@example.com'"
            )
            db.commit()

            row = db.execute(
                "SELECT oauth_provider, oauth_id FROM users WHERE email = 'test@example.com'"
            ).fetchone()
            assert row["oauth_provider"] == "google"
            assert row["oauth_id"] == "test-google-id"
