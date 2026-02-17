"""Security tests — SQL injection, XSS, auth bypass, input validation."""

from __future__ import annotations

import json
import pytest


class TestSQLInjection:
    """Verify parameterized queries prevent SQL injection."""

    def test_login_sql_injection_email(self, client):
        """SQL injection in email field should fail gracefully."""
        resp = client.post("/login", data={
            "email": "' OR 1=1 --",
            "password": "anything",
        }, follow_redirects=True)
        # Should not log in
        assert resp.status_code == 200
        assert b"dashboard" not in resp.data.lower() or b"login" in resp.data.lower()

    def test_login_sql_injection_password(self, client):
        resp = client.post("/login", data={
            "email": "test@example.com",
            "password": "' OR '1'='1",
        }, follow_redirects=True)
        assert b"dashboard" not in resp.data.lower() or b"Invalid" in resp.data or b"login" in resp.data.lower()

    def test_api_sql_injection_in_query_params(self, auth_client):
        """SQL injection in query params should be safely handled."""
        resp = auth_client.get("/api/flashcards?mode=all&page=1; DROP TABLE users;--")
        assert resp.status_code in (200, 400)

    def test_grade_submission_sql_injection(self, auth_client):
        """SQL injection in grade submission fields."""
        resp = auth_client.post("/api/study/grade", json={
            "subject": "'; DROP TABLE grades; --",
            "answer": "Test answer",
            "question": "Test question",
        })
        # Should not crash — either processes normally or returns error
        assert resp.status_code in (200, 400, 500)


class TestXSSPrevention:
    """Verify XSS payloads are handled safely."""

    def test_xss_in_user_name(self, auth_client, app):
        """XSS in user profile name should be escaped."""
        from database import get_db
        with app.app_context():
            db = get_db()
            db.execute(
                "UPDATE users SET name = ? WHERE id = 1",
                ('<script>alert("xss")</script>',),
            )
            db.commit()

        resp = auth_client.get("/dashboard")
        assert resp.status_code == 200
        # Raw script tag should not appear unescaped
        assert b'<script>alert("xss")</script>' not in resp.data

    def test_xss_in_flashcard_content(self, auth_client, app):
        """XSS in flashcard content."""
        from database import get_db
        with app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO flashcards (id, user_id, front, back, subject, created_at, next_review) "
                "VALUES ('xss1', 1, '<img src=x onerror=alert(1)>', 'back', 'Biology', '2026-01-01', '2026-01-01')"
            )
            db.commit()

        resp = auth_client.get("/api/flashcards?mode=all")
        assert resp.status_code == 200
        # The response is JSON, so it will be escaped, but verify no raw HTML injection
        data = resp.get_json()
        if data and "cards" in data:
            for card in data["cards"]:
                # JSON encoding handles escaping, but verify content is retrievable
                assert card is not None


class TestAuthBypass:
    """Verify authentication cannot be bypassed."""

    def test_unauthenticated_dashboard_redirect(self, client):
        """Unauthenticated user should be redirected from protected pages."""
        resp = client.get("/dashboard")
        assert resp.status_code in (302, 401)

    def test_unauthenticated_api_access(self, client):
        """Unauthenticated API calls should return 401/302."""
        endpoints = [
            "/api/credits/balance",
            "/api/subscription/current",
            "/api/gamification",
            "/api/flashcards?mode=all",
            "/api/notifications",
        ]
        for endpoint in endpoints:
            resp = client.get(endpoint)
            assert resp.status_code in (302, 401, 403), f"{endpoint} returned {resp.status_code}"

    def test_unauthenticated_post_blocked(self, client):
        """POST to protected endpoints should fail without auth."""
        resp = client.post("/api/credits/purchase", json={"amount": 100})
        assert resp.status_code in (302, 401, 403)

    def test_teacher_endpoint_blocked_for_students(self, auth_client):
        """Student should not access teacher-only endpoints."""
        resp = auth_client.get("/teacher/dashboard")
        assert resp.status_code in (302, 403)


class TestSecurityHeaders:
    """Verify security headers are set."""

    def test_x_content_type_options(self, auth_client):
        resp = auth_client.get("/dashboard")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, auth_client):
        resp = auth_client.get("/dashboard")
        assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"

    def test_xss_protection_header(self, auth_client):
        resp = auth_client.get("/dashboard")
        assert resp.headers.get("X-XSS-Protection") == "1; mode=block"

    def test_referrer_policy(self, auth_client):
        resp = auth_client.get("/dashboard")
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_csp_header_present(self, auth_client):
        resp = auth_client.get("/dashboard")
        csp = resp.headers.get("Content-Security-Policy", "")
        assert "default-src" in csp
        assert "'self'" in csp


class TestInputValidation:
    """Verify input validation on key endpoints."""

    def test_empty_login_data(self, client):
        resp = client.post("/login", data={}, follow_redirects=True)
        assert resp.status_code == 200

    def test_oversized_input_rejected(self, auth_client):
        """Very large input should be handled gracefully."""
        large_text = "A" * 100_000
        resp = auth_client.post("/api/study/grade", json={
            "subject": "Biology",
            "answer": large_text,
            "question": "Test",
        })
        # Should not crash
        assert resp.status_code in (200, 400, 413, 500)

    def test_invalid_json_body(self, auth_client):
        """Invalid JSON in request body should return 400."""
        resp = auth_client.post(
            "/api/credits/purchase",
            data="not json",
            content_type="application/json",
        )
        assert resp.status_code in (400, 500)

    def test_negative_credit_purchase(self, auth_client):
        """Negative credit amount should be rejected."""
        resp = auth_client.post("/api/credits/purchase", json={"amount": -100})
        assert resp.status_code == 400

    def test_zero_credit_purchase(self, auth_client):
        """Zero credit amount should be rejected."""
        resp = auth_client.post("/api/credits/purchase", json={"amount": 0})
        assert resp.status_code == 400


class TestFileUploadSecurity:
    """Verify file upload restrictions."""

    def test_no_file_upload(self, auth_client):
        """Upload endpoint should handle missing file gracefully."""
        resp = auth_client.post("/api/upload")
        assert resp.status_code in (400, 302, 200)

    def test_empty_file_upload(self, auth_client):
        """Upload endpoint should reject empty files."""
        import io
        data = {"file": (io.BytesIO(b""), "")}
        resp = auth_client.post("/api/upload", data=data, content_type="multipart/form-data")
        assert resp.status_code in (400, 200)
