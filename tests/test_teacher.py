"""Tests for teacher dashboard, analytics, and SOS alerts."""

import json
import pytest
from datetime import datetime


class TestTeacherDashboard:
    def test_teacher_dashboard_loads(self, teacher_client):
        resp = teacher_client.get("/teacher/dashboard")
        assert resp.status_code == 200
        assert b"Teacher Dashboard" in resp.data

    def test_teacher_class_detail_loads(self, teacher_client):
        resp = teacher_client.get("/teacher/classes/1")
        assert resp.status_code == 200
        assert b"Biology HL" in resp.data

    def test_teacher_class_detail_wrong_teacher(self, auth_client, app):
        """Non-teacher user should be blocked from teacher pages."""
        resp = auth_client.get("/teacher/classes/1", follow_redirects=False)
        assert resp.status_code in (302, 403)

    def test_teacher_stats_api(self, teacher_client):
        resp = teacher_client.get("/api/teacher/stats")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "class_count" in data
        assert data["class_count"] >= 1


class TestTeacherAnalytics:
    def test_grade_distribution(self, teacher_client, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute(
                "INSERT INTO grades (user_id, subject, subject_display, level, command_term, "
                "grade, percentage, mark_earned, mark_total, topic, timestamp) "
                "VALUES (1, 'biology', 'Biology', 'HL', 'Explain', 5, 68, 3, 4, 'Topic 1', '2026-01-15')"
            )
            db.commit()

        resp = teacher_client.get("/api/teacher/class/1/grade-distribution")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "grade_distribution" in data

    def test_activity_heatmap(self, teacher_client, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute(
                "INSERT INTO activity_log (user_id, date, subject, questions_attempted, "
                "questions_answered, duration_minutes, timestamp) "
                "VALUES (1, ?, 'Biology', 5, 5, 30, ?)",
                (datetime.now().strftime("%Y-%m-%d"), datetime.now().isoformat()),
            )
            db.commit()

        resp = teacher_client.get("/api/teacher/class/1/activity-heatmap")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "activity_heatmap" in data

    def test_command_term_breakdown(self, teacher_client, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute(
                "INSERT INTO grades (user_id, subject, subject_display, level, command_term, "
                "grade, percentage, mark_earned, mark_total, topic, timestamp) "
                "VALUES (1, 'biology', 'Biology', 'HL', 'Evaluate', 6, 75, 6, 8, 'Topic 2', '2026-01-20')"
            )
            db.commit()

        resp = teacher_client.get("/api/teacher/class/1/command-term-breakdown")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "command_term_breakdown" in data

    def test_topic_gaps(self, teacher_client, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            for i in range(3):
                db.execute(
                    "INSERT INTO grades (user_id, subject, subject_display, level, command_term, "
                    "grade, percentage, mark_earned, mark_total, topic, timestamp) "
                    "VALUES (1, 'biology', 'Biology', 'HL', 'Define', 3, 40, 1, 4, 'Weak Topic', ?)",
                    (f"2026-01-{10+i}",),
                )
            db.commit()

        resp = teacher_client.get("/api/teacher/class/1/topic-gaps")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "topic_gaps" in data

    def test_at_risk_students(self, teacher_client):
        resp = teacher_client.get("/api/teacher/class/1/at-risk")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "at_risk_students" in data


class TestTeacherSOS:
    def test_sos_alerts_endpoint(self, teacher_client):
        resp = teacher_client.get("/api/teacher/sos-alerts")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "alerts" in data

    def test_sos_alerts_with_data(self, teacher_client, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute(
                "INSERT INTO sos_alerts (user_id, subject, topic, failure_count, "
                "avg_percentage, status, created_at) "
                "VALUES (1, 'Biology', 'Cell Division', 5, 30.0, 'active', '2026-01-15')"
            )
            db.commit()

        resp = teacher_client.get("/api/teacher/sos-alerts")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["alerts"]) >= 1
        assert data["alerts"][0]["student_name"] == "Test Student"

    def test_sos_status_endpoint(self, auth_client):
        resp = auth_client.get("/api/sos/status")
        assert resp.status_code == 200
