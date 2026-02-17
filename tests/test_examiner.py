"""Tests for examiner review pipeline UI endpoints."""

import json
import pytest
from datetime import datetime


class TestExaminerDashboard:
    def test_examiner_dashboard_loads(self, teacher_client):
        resp = teacher_client.get("/teacher/examiner")
        assert resp.status_code == 200
        assert b"Examiner Dashboard" in resp.data

    def test_reviews_queue(self, teacher_client):
        resp = teacher_client.get("/api/reviews/queue")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "reviews" in data

    def test_reviews_assigned_empty(self, teacher_client):
        resp = teacher_client.get("/api/reviews/assigned")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "reviews" in data
        assert len(data["reviews"]) == 0


class TestStudentReviews:
    def test_student_reviews_page_loads(self, auth_client):
        resp = auth_client.get("/reviews")
        assert resp.status_code == 200
        assert b"My Submitted Reviews" in resp.data

    def test_student_reviews_mine(self, auth_client):
        resp = auth_client.get("/api/reviews/mine")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "reviews" in data


class TestExaminerReviewFlow:
    def test_assign_and_complete_review(self, teacher_client, app):
        # Create a review directly in DB
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute(
                "INSERT INTO examiner_reviews "
                "(user_id, doc_type, subject, title, submission_text, status, submitted_at) "
                "VALUES (1, 'ia', 'Biology', 'Test IA', 'My submission text', 'submitted', ?)",
                (datetime.now().isoformat(),),
            )
            db.commit()
            row = db.execute("SELECT id FROM examiner_reviews ORDER BY id DESC LIMIT 1").fetchone()
            review_id = row["id"]

        # Assign
        resp = teacher_client.post(f"/api/reviews/{review_id}/assign")
        assert resp.status_code == 200

        # Verify assigned
        resp = teacher_client.get("/api/reviews/assigned")
        data = resp.get_json()
        assert any(r["id"] == review_id for r in data["reviews"])

        # Complete
        resp = teacher_client.post(f"/api/reviews/{review_id}/complete",
            data=json.dumps({
                "feedback": "Great work, minor improvements needed.",
                "grade": "B",
                "video_url": "",
            }),
            content_type="application/json",
        )
        assert resp.status_code == 200
