"""Email verification tests."""

from __future__ import annotations

import pytest
from database import get_db


class TestEmailVerification:
    """Test email verification flow."""

    def test_register_does_not_auto_login(self, app, client):
        """After registration, user should NOT be logged in."""
        resp = client.post("/register", data={
            "name": "New User",
            "email": "new@example.com",
            "password": "StrongPass1",
            "confirm_password": "StrongPass1",
        }, follow_redirects=True)
        assert resp.status_code == 200
        # Should be on login page, not dashboard
        assert b"login" in resp.data.lower() or b"verify" in resp.data.lower()

    def test_register_creates_verification_token(self, app, client):
        """Registration should create a verification token."""
        client.post("/register", data={
            "name": "Token User",
            "email": "token@example.com",
            "password": "StrongPass1",
            "confirm_password": "StrongPass1",
        })
        with app.app_context():
            db = get_db()
            row = db.execute(
                "SELECT email_verified, email_verification_token FROM users WHERE email = ?",
                ("token@example.com",),
            ).fetchone()
            assert row is not None
            assert row["email_verified"] == 0
            assert len(row["email_verification_token"]) > 0

    def test_unverified_user_cannot_login(self, app, client):
        """Unverified user should be blocked from login."""
        from werkzeug.security import generate_password_hash
        # Register user
        client.post("/register", data={
            "name": "Unverified",
            "email": "unverified@example.com",
            "password": "StrongPass1",
            "confirm_password": "StrongPass1",
        })

        with app.app_context():
            db = get_db()
            db.execute(
                "UPDATE users SET password_hash = ? WHERE email = ?",
                (generate_password_hash("StrongPass1"), "unverified@example.com"),
            )
            db.commit()

        resp = client.post("/login", data={
            "email": "unverified@example.com",
            "password": "StrongPass1",
        }, follow_redirects=True)
        assert b"verify" in resp.data.lower()

    def test_verify_email_with_valid_token(self, app, client):
        """Valid verification token should verify the email."""
        # Register
        client.post("/register", data={
            "name": "Verify Me",
            "email": "verifyme@example.com",
            "password": "StrongPass1",
            "confirm_password": "StrongPass1",
        })

        with app.app_context():
            db = get_db()
            row = db.execute(
                "SELECT email_verification_token FROM users WHERE email = ?",
                ("verifyme@example.com",),
            ).fetchone()
            token = row["email_verification_token"]

        resp = client.get(f"/verify-email/{token}", follow_redirects=True)
        assert resp.status_code == 200

        with app.app_context():
            db = get_db()
            row = db.execute(
                "SELECT email_verified, email_verification_token FROM users WHERE email = ?",
                ("verifyme@example.com",),
            ).fetchone()
            assert row["email_verified"] == 1
            assert row["email_verification_token"] == ""

    def test_verify_email_with_invalid_token(self, client):
        """Invalid token should show error."""
        resp = client.get("/verify-email/invalid-token-xyz", follow_redirects=True)
        assert resp.status_code == 200
        assert b"invalid" in resp.data.lower() or b"expired" in resp.data.lower()

    def test_resend_verification(self, app, client):
        """Resend verification should generate new token."""
        client.post("/register", data={
            "name": "Resend User",
            "email": "resend@example.com",
            "password": "StrongPass1",
            "confirm_password": "StrongPass1",
        })

        with app.app_context():
            db = get_db()
            row = db.execute(
                "SELECT email_verification_token FROM users WHERE email = ?",
                ("resend@example.com",),
            ).fetchone()
            old_token = row["email_verification_token"]

        resp = client.post("/resend-verification", data={
            "email": "resend@example.com",
        }, follow_redirects=True)
        assert resp.status_code == 200

        with app.app_context():
            db = get_db()
            row = db.execute(
                "SELECT email_verification_token FROM users WHERE email = ?",
                ("resend@example.com",),
            ).fetchone()
            assert row["email_verification_token"] != old_token

    def test_verified_user_can_login(self, app, client):
        """After verification, user should be able to login."""
        from werkzeug.security import generate_password_hash
        # Register
        client.post("/register", data={
            "name": "Verified User",
            "email": "verified@example.com",
            "password": "StrongPass1",
            "confirm_password": "StrongPass1",
        })

        # Get token and verify
        with app.app_context():
            db = get_db()
            row = db.execute(
                "SELECT email_verification_token FROM users WHERE email = ?",
                ("verified@example.com",),
            ).fetchone()
            token = row["email_verification_token"]

        client.get(f"/verify-email/{token}")

        # Now login should work
        resp = client.post("/login", data={
            "email": "verified@example.com",
            "password": "StrongPass1",
        }, follow_redirects=False)
        assert resp.status_code == 302
        assert "/dashboard" in resp.headers.get("Location", "") or "/onboarding" in resp.headers.get("Location", "")
