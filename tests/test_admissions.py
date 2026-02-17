"""Tests for admissions page and deadline tracker."""

import json
import pytest


class TestAdmissionsPage:
    def test_admissions_page_loads(self, auth_client):
        resp = auth_client.get("/admissions")
        assert resp.status_code == 200
        assert b"University Admissions" in resp.data

    def test_admissions_profile_endpoint(self, auth_client):
        resp = auth_client.get("/api/admissions/profile")
        # Should return 200 even if profile generation fails (mock Gemini)
        assert resp.status_code == 200


class TestAdmissionsDeadlines:
    def test_add_deadline(self, auth_client):
        resp = auth_client.post("/api/admissions/deadlines",
            data=json.dumps({
                "university": "Oxford",
                "program": "PPE",
                "deadline_date": "2026-10-15",
                "deadline_type": "application",
                "notes": "UCAS deadline",
            }),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "deadline_id" in data

    def test_list_deadlines(self, auth_client):
        # Add a deadline first
        auth_client.post("/api/admissions/deadlines",
            data=json.dumps({
                "university": "Cambridge",
                "deadline_date": "2026-10-15",
            }),
            content_type="application/json",
        )
        resp = auth_client.get("/api/admissions/deadlines")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "deadlines" in data
        assert len(data["deadlines"]) >= 1

    def test_update_deadline_status(self, auth_client):
        # Add a deadline
        resp = auth_client.post("/api/admissions/deadlines",
            data=json.dumps({
                "university": "MIT",
                "deadline_date": "2026-01-01",
            }),
            content_type="application/json",
        )
        dl_id = resp.get_json()["deadline_id"]

        # Update it
        resp = auth_client.put(f"/api/admissions/deadlines/{dl_id}",
            data=json.dumps({"status": "submitted"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

        # Verify the update
        resp = auth_client.get("/api/admissions/deadlines")
        deadlines = resp.get_json()["deadlines"]
        updated = [d for d in deadlines if d["id"] == dl_id]
        assert updated[0]["status"] == "submitted"

    def test_add_deadline_requires_fields(self, auth_client):
        resp = auth_client.post("/api/admissions/deadlines",
            data=json.dumps({"university": ""}),
            content_type="application/json",
        )
        assert resp.status_code == 400
