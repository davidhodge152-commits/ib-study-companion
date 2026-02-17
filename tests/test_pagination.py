"""Tests for pagination helpers and paginated API endpoints."""

from __future__ import annotations

import json
import pytest


class TestPaginateArgs:
    def test_defaults(self, app):
        with app.test_request_context("/api/test"):
            from helpers import paginate_args
            page, limit = paginate_args()
            assert page == 1
            assert limit == 20

    def test_custom_page_and_limit(self, app):
        with app.test_request_context("/api/test?page=3&limit=10"):
            from helpers import paginate_args
            page, limit = paginate_args()
            assert page == 3
            assert limit == 10

    def test_max_limit_enforced(self, app):
        with app.test_request_context("/api/test?limit=500"):
            from helpers import paginate_args
            page, limit = paginate_args(max_limit=100)
            assert limit == 100

    def test_invalid_values_use_defaults(self, app):
        with app.test_request_context("/api/test?page=abc&limit=xyz"):
            from helpers import paginate_args
            page, limit = paginate_args(default_limit=15)
            assert page == 1
            assert limit == 15

    def test_negative_page_clamps_to_one(self, app):
        with app.test_request_context("/api/test?page=-5"):
            from helpers import paginate_args
            page, limit = paginate_args()
            assert page == 1


class TestPaginatedResponse:
    def test_basic_envelope(self):
        from helpers import paginated_response
        result = paginated_response(["a", "b", "c"], total=10, page=1, limit=3)
        assert result["items"] == ["a", "b", "c"]
        assert result["pagination"]["total"] == 10
        assert result["pagination"]["page"] == 1
        assert result["pagination"]["limit"] == 3
        assert result["pagination"]["pages"] == 4  # ceil(10/3)

    def test_single_page(self):
        from helpers import paginated_response
        result = paginated_response(["x"], total=1, page=1, limit=20)
        assert result["pagination"]["pages"] == 1


class TestPaginatedEndpoints:
    def test_flashcards_pagination(self, auth_client, app):
        # Create some flashcards
        with app.app_context():
            from database import get_db
            db = get_db()
            for i in range(5):
                db.execute(
                    "INSERT INTO flashcards (id, user_id, front, back, subject, created_at, next_review) "
                    "VALUES (?, 1, ?, ?, 'Biology', '2026-01-01', '2026-01-01')",
                    (f"fc_{i}", f"Q{i}", f"A{i}"),
                )
            db.commit()

        resp = auth_client.get("/api/flashcards?mode=all&page=1&limit=2")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "pagination" in data
        assert data["pagination"]["limit"] == 2
        assert data["pagination"]["total"] == 5
        assert len(data["cards"]) == 2

    def test_notifications_pagination(self, auth_client, app):
        resp = auth_client.get("/api/notifications?page=1&limit=5")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "pagination" in data
        assert "unread_count" in data

    def test_misconceptions_pagination(self, auth_client):
        resp = auth_client.get("/api/misconceptions?page=1&limit=10")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "pagination" in data

    def test_mock_reports_pagination(self, auth_client):
        resp = auth_client.get("/api/mock-reports?page=1&limit=5")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "pagination" in data

    def test_tutor_history_pagination(self, auth_client):
        resp = auth_client.get("/api/tutor/history?page=1&limit=5")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "pagination" in data

    def test_groups_pagination(self, auth_client):
        resp = auth_client.get("/api/groups?page=1&limit=5")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "pagination" in data
