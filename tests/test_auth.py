"""Tests for auth.py — register, login, logout, protected routes, lockout."""

import pytest
from datetime import datetime, timedelta
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
            "password": "Securepass123",
            "confirm_password": "Securepass123",
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_register_password_mismatch(self, client):
        resp = client.post("/register", data={
            "name": "User",
            "email": "mismatch@test.com",
            "password": "Pass1234",
            "confirm_password": "Different1",
        })
        assert b"Passwords do not match" in resp.data

    def test_register_short_password(self, client):
        resp = client.post("/register", data={
            "name": "User",
            "email": "short@test.com",
            "password": "Ab1",
            "confirm_password": "Ab1",
        })
        assert b"at least 8" in resp.data

    def test_register_duplicate_email(self, app, client):
        # First registration
        client.post("/register", data={
            "name": "First",
            "email": "dupe@test.com",
            "password": "Pass123456",
            "confirm_password": "Pass123456",
        })
        # Log out so second registration attempt isn't auto-redirected
        client.get("/logout")
        # Second with same email
        resp = client.post("/register", data={
            "name": "Second",
            "email": "dupe@test.com",
            "password": "Pass123456",
            "confirm_password": "Pass123456",
        })
        assert b"already exists" in resp.data


class TestTeacherRegister:
    def test_teacher_register_page_loads(self, client):
        resp = client.get("/register/teacher")
        assert resp.status_code == 200
        assert b"Teacher Registration" in resp.data

    def test_teacher_register_success(self, app, client):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute(
                "INSERT INTO schools (name, code, created_at) VALUES ('Test School', 'TEACH01', '2026-01-01')"
            )
            db.commit()

        resp = client.post("/register/teacher", data={
            "name": "New Teacher",
            "email": "newteacher@test.com",
            "password": "TeacherPass1",
            "confirm_password": "TeacherPass1",
            "school_code": "TEACH01",
        }, follow_redirects=True)
        assert resp.status_code == 200

        with app.app_context():
            from database import get_db
            db = get_db()
            row = db.execute("SELECT role, school_id FROM users WHERE email='newteacher@test.com'").fetchone()
            assert row["role"] == "teacher"
            assert row["school_id"] is not None

    def test_teacher_register_invalid_school_code(self, client):
        resp = client.post("/register/teacher", data={
            "name": "Bad Teacher",
            "email": "bad@test.com",
            "password": "TeacherPass1",
            "confirm_password": "TeacherPass1",
            "school_code": "INVALID",
        })
        assert b"Invalid school code" in resp.data

    def test_teacher_register_sets_role(self, app, client):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute(
                "INSERT INTO schools (name, code, created_at) VALUES ('Another School', 'ROLE01', '2026-01-01')"
            )
            db.commit()

        client.post("/register/teacher", data={
            "name": "Role Teacher",
            "email": "role@test.com",
            "password": "RolePass123",
            "confirm_password": "RolePass123",
            "school_code": "ROLE01",
        })

        with app.app_context():
            from database import get_db
            db = get_db()
            row = db.execute("SELECT role FROM users WHERE email='role@test.com'").fetchone()
            assert row is not None
            assert row["role"] == "teacher"


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


class TestLoginLockout:
    def test_login_lockout_after_5_failures(self, app, client):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute(
                "UPDATE users SET password_hash = ? WHERE id = 1",
                (generate_password_hash("correct"),),
            )
            db.commit()

        for _ in range(5):
            client.post("/login", data={
                "email": "test@example.com",
                "password": "wrong",
            })

        resp = client.post("/login", data={
            "email": "test@example.com",
            "password": "correct",
        })
        assert b"temporarily locked" in resp.data

    def test_lockout_resets_on_success(self, app, client):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute(
                "UPDATE users SET password_hash = ?, login_attempts = 3 WHERE id = 1",
                (generate_password_hash("correct"),),
            )
            db.commit()

        resp = client.post("/login", data={
            "email": "test@example.com",
            "password": "correct",
        }, follow_redirects=False)
        assert resp.status_code in (302, 200)

        with app.app_context():
            from database import get_db
            db = get_db()
            row = db.execute("SELECT login_attempts FROM users WHERE id = 1").fetchone()
            assert row["login_attempts"] == 0

    def test_lockout_expires(self, app, client):
        with app.app_context():
            from database import get_db
            db = get_db()
            past = (datetime.now() - timedelta(minutes=1)).isoformat()
            db.execute(
                "UPDATE users SET password_hash = ?, login_attempts = 5, locked_until = ? WHERE id = 1",
                (generate_password_hash("correct"), past),
            )
            db.commit()

        resp = client.post("/login", data={
            "email": "test@example.com",
            "password": "correct",
        }, follow_redirects=False)
        assert resp.status_code in (302, 200)


class TestLogout:
    def test_logout_redirects(self, auth_client):
        resp = auth_client.get("/logout", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers.get("Location", "")


class TestAuditLog:
    def test_audit_log_login_success(self, app, client):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute(
                "UPDATE users SET password_hash = ? WHERE id = 1",
                (generate_password_hash("Correct1"),),
            )
            db.commit()

        client.post("/login", data={
            "email": "test@example.com",
            "password": "Correct1",
        })

        with app.app_context():
            from database import get_db
            db = get_db()
            row = db.execute(
                "SELECT * FROM audit_log WHERE action = 'login_success'"
            ).fetchone()
            assert row is not None
            assert row["user_id"] == 1

    def test_audit_log_login_failed(self, app, client):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute(
                "UPDATE users SET password_hash = ? WHERE id = 1",
                (generate_password_hash("Correct1"),),
            )
            db.commit()

        client.post("/login", data={
            "email": "test@example.com",
            "password": "Wrong1",
        })

        with app.app_context():
            from database import get_db
            db = get_db()
            row = db.execute(
                "SELECT * FROM audit_log WHERE action = 'login_failed'"
            ).fetchone()
            assert row is not None

    def test_audit_log_register(self, app, client):
        client.post("/register", data={
            "name": "Audit User",
            "email": "audit@test.com",
            "password": "AuditPass1",
            "confirm_password": "AuditPass1",
        })

        with app.app_context():
            from database import get_db
            db = get_db()
            row = db.execute(
                "SELECT * FROM audit_log WHERE action = 'register'"
            ).fetchone()
            assert row is not None
            assert "audit@test.com" in row["detail"]


class TestPasswordReset:
    def test_forgot_password_page_loads(self, client):
        resp = client.get("/forgot-password")
        assert resp.status_code == 200
        assert b"Reset your password" in resp.data

    def test_forgot_password_always_shows_success(self, client):
        resp = client.post("/forgot-password", data={
            "email": "nonexistent@test.com",
        })
        assert b"If an account exists" in resp.data

    def test_reset_password_full_flow(self, app, client):
        import secrets
        from werkzeug.security import generate_password_hash as gen_hash
        token = secrets.token_urlsafe(32)
        token_hash = gen_hash(token)

        with app.app_context():
            from database import get_db
            db = get_db()
            expires = (datetime.now() + timedelta(hours=1)).isoformat()
            db.execute(
                "UPDATE users SET reset_token=?, reset_token_expires=? WHERE id=1",
                (token_hash, expires),
            )
            db.commit()

        # GET the reset page
        resp = client.get(f"/reset-password/1/{token}")
        assert resp.status_code == 200
        assert b"Set a new password" in resp.data

        # POST with new password
        resp = client.post(f"/reset-password/1/{token}", data={
            "password": "NewPass123",
            "confirm_password": "NewPass123",
        }, follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers.get("Location", "")

    def test_reset_password_expired_token(self, app, client):
        import secrets
        from werkzeug.security import generate_password_hash as gen_hash
        token = secrets.token_urlsafe(32)
        token_hash = gen_hash(token)

        with app.app_context():
            from database import get_db
            db = get_db()
            past = (datetime.now() - timedelta(hours=2)).isoformat()
            db.execute(
                "UPDATE users SET reset_token=?, reset_token_expires=? WHERE id=1",
                (token_hash, past),
            )
            db.commit()

        resp = client.get(f"/reset-password/1/{token}")
        assert b"expired" in resp.data

    def test_reset_password_invalid_token(self, client):
        resp = client.get("/reset-password/1/badtoken")
        assert b"Invalid" in resp.data


class TestGDPR:
    def test_account_export(self, app, auth_client):
        resp = auth_client.get("/api/account/export")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "user" in data
        assert "exported_at" in data
        assert data["user"]["email"] == "test@example.com"

    def test_account_delete_requires_password(self, app, auth_client):
        resp = auth_client.post("/api/account/delete", data={})
        assert resp.status_code == 400

    def test_account_delete_wrong_password(self, app, auth_client):
        resp = auth_client.post("/api/account/delete", data={
            "password": "WrongPass1",
        })
        assert resp.status_code == 403

    def test_account_delete_success(self, app, client):
        # Register a new account, then delete it
        client.post("/register", data={
            "name": "Delete Me",
            "email": "deleteme@test.com",
            "password": "DeleteMe1",
            "confirm_password": "DeleteMe1",
        })
        resp = client.post("/api/account/delete", data={
            "password": "DeleteMe1",
        })
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True


class TestParentTokenExpiry:
    def test_expired_parent_token_returns_none(self, app):
        with app.app_context():
            from database import get_db
            from db_stores import ParentConfigDB
            db = get_db()
            # Set up parent config with expired token
            db.execute("INSERT OR IGNORE INTO parent_config (user_id, enabled, token) VALUES (1, 1, 'testtoken')")
            past = (datetime.now() - timedelta(days=1)).isoformat()
            db.execute("UPDATE parent_config SET token_expires_at=? WHERE user_id=1", (past,))
            db.commit()

            result = ParentConfigDB.load_by_token("testtoken")
            assert result is None

    def test_valid_parent_token_loads(self, app):
        with app.app_context():
            from database import get_db
            from db_stores import ParentConfigDB
            db = get_db()
            future = (datetime.now() + timedelta(days=30)).isoformat()
            db.execute("INSERT OR IGNORE INTO parent_config (user_id, enabled, token) VALUES (1, 1, 'validtoken')")
            db.execute("UPDATE parent_config SET token='validtoken', token_expires_at=? WHERE user_id=1", (future,))
            db.commit()

            result = ParentConfigDB.load_by_token("validtoken")
            assert result is not None
            assert result.user_id == 1


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
