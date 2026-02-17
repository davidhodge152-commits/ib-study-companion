"""Tests for enhanced study features: review calendar, weak topics, exam history."""

import json
import pytest
from datetime import datetime, timedelta


class TestReviewCalendar:
    def test_review_calendar_empty(self, auth_client):
        resp = auth_client.get("/api/study/review-calendar")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "calendar" in data
        assert isinstance(data["calendar"], dict)

    def test_review_calendar_with_data(self, auth_client, app):
        tomorrow = (datetime.now() + timedelta(days=1)).isoformat()
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute(
                "INSERT INTO review_schedule (user_id, subject, topic, command_term, next_review, interval_days) "
                "VALUES (1, 'Biology', 'Photosynthesis', 'Explain', ?, 3)",
                (tomorrow,),
            )
            db.commit()

        resp = auth_client.get("/api/study/review-calendar")
        data = resp.get_json()
        assert len(data["calendar"]) >= 1
        # Should have at least one item
        items = list(data["calendar"].values())
        assert any(len(day_items) > 0 for day_items in items)


class TestWeakTopics:
    def test_weak_topics_empty(self, auth_client):
        resp = auth_client.get("/api/study/weak-topics")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "weak_topics" in data
        assert "sos_alerts" in data

    def test_weak_topics_with_data(self, auth_client, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute(
                "INSERT INTO topic_progress (user_id, subject, topic_id, subtopic, attempts, avg_percentage, last_practiced) "
                "VALUES (1, 'Biology', 'topic-1', 'Cell Respiration', 5, 30.0, '2026-01-15')"
            )
            db.execute(
                "INSERT INTO topic_progress (user_id, subject, topic_id, subtopic, attempts, avg_percentage, last_practiced) "
                "VALUES (1, 'Chemistry', 'topic-2', 'Bonding', 1, 60.0, '2026-01-20')"
            )
            db.commit()

        resp = auth_client.get("/api/study/weak-topics")
        data = resp.get_json()
        # Should include Cell Respiration (30% < 50) and Bonding (1 attempt < 3)
        assert len(data["weak_topics"]) >= 2
        subjects = [t["subject"] for t in data["weak_topics"]]
        assert "Biology" in subjects


class TestExamHistory:
    def test_exam_history_empty(self, auth_client):
        resp = auth_client.get("/api/study/exam-history")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "sessions" in data
        assert len(data["sessions"]) == 0

    def test_exam_history_with_data(self, auth_client, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            questions = json.dumps([
                {"question": "Explain photosynthesis", "command_term": "Explain", "marks": 4},
                {"question": "Define osmosis", "command_term": "Define", "marks": 2},
            ])
            answers = json.dumps([
                {"answer": "Process of...", "marks_earned": 3},
                {"answer": "Movement of...", "marks_earned": 2},
            ])
            db.execute(
                "INSERT INTO exam_sessions (user_id, subject, level, paper_number, duration_minutes, "
                "started_at, completed_at, total_marks, earned_marks, grade, questions, answers) "
                "VALUES (1, 'Biology', 'HL', 1, 45, '2026-01-15T10:00:00', '2026-01-15T10:45:00', 6, 5, 6, ?, ?)",
                (questions, answers),
            )
            db.commit()

        resp = auth_client.get("/api/study/exam-history")
        data = resp.get_json()
        assert len(data["sessions"]) == 1
        session = data["sessions"][0]
        assert session["subject"] == "Biology"
        assert session["earned_marks"] == 5
        assert session["total_marks"] == 6
        assert session["percentage"] == 83.3
        # Command term breakdown should be present
        assert "Explain" in session["command_term_breakdown"]
        assert session["command_term_breakdown"]["Explain"]["earned"] == 3
