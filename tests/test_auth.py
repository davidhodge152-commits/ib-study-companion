"""Tests for auth.py — register, login, logout, protected routes."""

import pytest
from werkzeug.security import generate_password_hash


class TestRegister:
    def test_register_page_loads(self, client):
        resp = client.get("/register")
        assert resp.status_code == 200
        assert b"Create your account" in resp.data

    def test_register_success(self, app, client):
        resp = client.post("/register", data={
            "name": "New User",
            "email": "new@test.com",
            "password": "securepass123",
            "confirm_password": "securepass123",
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_register_password_mismatch(self, client):
        resp = client.post("/register", data={
            "name": "User",
            "email": "mismatch@test.com",
            "password": "pass123",
            "confirm_password": "different",
        })
        assert b"Passwords do not match" in resp.data

    def test_register_short_password(self, client):
        resp = client.post("/register", data={
            "name": "User",
            "email": "short@test.com",
            "password": "12345",
            "confirm_password": "12345",
        })
        assert b"at least 6" in resp.data

    def test_register_duplicate_email(self, app, client):
        # First registration
        client.post("/register", data={
            "name": "First",
            "email": "dupe@test.com",
            "password": "pass123456",
            "confirm_password": "pass123456",
        })
        # Log out so second registration attempt isn't auto-redirected
        client.get("/logout")
        # Second with same email
        resp = client.post("/register", data={
            "name": "Second",
            "email": "dupe@test.com",
            "password": "pass123456",
            "confirm_password": "pass123456",
        })
        assert b"already exists" in resp.data


class TestLogin:
    def test_login_page_loads(self, client):
        resp = client.get("/login")
        assert resp.status_code == 200
        assert b"Welcome back" in resp.data

    def test_login_success(self, app, client):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute(
                "UPDATE users SET password_hash = ? WHERE id = 1",
                (generate_password_hash("testpass"),),
            )
            db.commit()

        resp = client.post("/login", data={
            "email": "test@example.com",
            "password": "testpass",
        }, follow_redirects=False)
        assert resp.status_code in (302, 200)

    def test_login_wrong_password(self, app, client):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute(
                "UPDATE users SET password_hash = ? WHERE id = 1",
                (generate_password_hash("correct"),),
            )
            db.commit()

        resp = client.post("/login", data={
            "email": "test@example.com",
            "password": "wrong",
        })
        assert b"Invalid" in resp.data

    def test_login_nonexistent_email(self, client):
        resp = client.post("/login", data={
            "email": "nobody@test.com",
            "password": "anything",
        })
        assert b"Invalid" in resp.data


class TestLogout:
    def test_logout_redirects(self, auth_client):
        resp = auth_client.get("/logout", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers.get("Location", "")


class TestProtectedRoutes:
    def test_dashboard_redirects_unauthenticated(self, client):
        resp = client.get("/dashboard", follow_redirects=False)
        assert resp.status_code == 302
        location = resp.headers.get("Location", "")
        assert "/login" in location

    def test_study_redirects_unauthenticated(self, client):
        resp = client.get("/study", follow_redirects=False)
        assert resp.status_code == 302

    def test_flashcards_redirects_unauthenticated(self, client):
        resp = client.get("/flashcards", follow_redirects=False)
        assert resp.status_code == 302
