"""Tests for predictive analytics, peer benchmarking, and insight endpoints."""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest


def _seed_grade_history(db, user_id: int, subject: str, count: int = 10):
    """Seed grade history for a user/subject with increasing grades."""
    base = datetime.now() - timedelta(days=count)
    for i in range(count):
        grade = min(7, 3 + (i * 4) // count)  # grades trend from 3 to 7
        pct = grade * 14
        ts = (base + timedelta(days=i)).isoformat()
        db.execute(
            "INSERT INTO grades (user_id, subject, subject_display, level, "
            "command_term, grade, percentage, mark_earned, mark_total, "
            "strengths, improvements, examiner_tip, topic, timestamp) "
            "VALUES (?, ?, ?, 'HL', 'Explain', ?, ?, 3, 4, '[]', '[]', '', 'Topic 1', ?)",
            (user_id, subject.lower(), subject, grade, pct, ts),
        )
    db.commit()


def _seed_activity_log(db, user_id: int, days: int = 15):
    """Seed activity log for study pattern analysis."""
    base = datetime.now() - timedelta(days=days)
    for i in range(days):
        dt = base + timedelta(days=i)
        db.execute(
            "INSERT INTO activity_log (user_id, date, subject, questions_attempted, "
            "duration_minutes, timestamp) VALUES (?, ?, 'Biology', ?, ?, ?)",
            (user_id, dt.strftime("%Y-%m-%d"), 3 + i % 5,
             20 + i * 2, dt.replace(hour=14 + (i % 3)).isoformat()),
        )
    db.commit()


class TestPredictiveGradeModel:
    def test_predict_subject_grade_sufficient_data(self, app):
        with app.app_context():
            from database import get_db
            from predictive_analytics import PredictiveGradeModel

            db = get_db()
            _seed_grade_history(db, 1, "Biology", count=10)

            model = PredictiveGradeModel()
            result = model.predict_subject_grade(1, "Biology")

            assert result is not None
            assert "predicted_grade" in result
            assert 1 <= result["predicted_grade"] <= 7
            assert len(result["confidence_interval"]) == 2
            assert result["confidence_interval"][0] <= result["confidence_interval"][1]
            assert result["trajectory"] in ("improving", "declining", "stable")
            assert result["data_points_used"] == 10
            assert "avg_percentage" in result

    def test_predict_subject_grade_insufficient_data(self, app):
        with app.app_context():
            from database import get_db
            from predictive_analytics import PredictiveGradeModel

            db = get_db()
            _seed_grade_history(db, 1, "Chemistry", count=3)

            model = PredictiveGradeModel()
            result = model.predict_subject_grade(1, "Chemistry")
            assert result is None

    def test_predict_total_ib_score(self, app):
        with app.app_context():
            from database import get_db
            from predictive_analytics import PredictiveGradeModel

            db = get_db()
            _seed_grade_history(db, 1, "Biology", count=8)
            _seed_grade_history(db, 1, "Mathematics: AA", count=8)

            model = PredictiveGradeModel()
            result = model.predict_total_ib_score(1)

            assert "subject_predictions" in result
            assert "predicted_subject_total" in result
            assert "core_bonus" in result
            assert "predicted_total" in result
            assert result["subjects_with_data"] >= 1

    def test_study_pattern_analysis_with_data(self, app):
        with app.app_context():
            from database import get_db
            from predictive_analytics import PredictiveGradeModel

            db = get_db()
            _seed_activity_log(db, 1, days=15)

            model = PredictiveGradeModel()
            result = model.study_pattern_analysis(1)

            assert result["total_sessions"] == 15
            assert result["best_hour"] is not None
            assert result["best_day"] is not None
            assert result["avg_session_minutes"] > 0
            assert 0 < result["consistency_score"] <= 1.0
            assert result["total_questions"] > 0

    def test_study_pattern_analysis_no_data(self, app):
        with app.app_context():
            from predictive_analytics import PredictiveGradeModel

            model = PredictiveGradeModel()
            result = model.study_pattern_analysis(1)

            assert result["total_sessions"] == 0
            assert result["best_hour"] is None
            assert result["consistency_score"] == 0.0

    def test_improving_trajectory(self, app):
        with app.app_context():
            from database import get_db
            from predictive_analytics import PredictiveGradeModel

            db = get_db()
            # Seed grades with clear upward trend
            base = datetime.now() - timedelta(days=10)
            for i in range(6):
                ts = (base + timedelta(days=i)).isoformat()
                db.execute(
                    "INSERT INTO grades (user_id, subject, subject_display, level, "
                    "command_term, grade, percentage, mark_earned, mark_total, "
                    "strengths, improvements, examiner_tip, topic, timestamp) "
                    "VALUES (1, 'physics', 'Physics', 'HL', 'Explain', ?, ?, 3, 4, "
                    "'[]', '[]', '', 'Topic 1', ?)",
                    (2 + i, (2 + i) * 14, ts),
                )
            db.commit()

            model = PredictiveGradeModel()
            result = model.predict_subject_grade(1, "Physics")
            assert result is not None
            assert result["trajectory"] == "improving"


class TestPeerPercentile:
    def test_insufficient_peers(self, app):
        with app.app_context():
            from database import get_db
            from community_analytics import peer_percentile

            db = get_db()
            _seed_grade_history(db, 1, "Biology", count=8)

            result = peer_percentile(1, "Biology")
            assert "error" in result
            assert result["sample_size"] < 10

    def test_sufficient_peers(self, app):
        with app.app_context():
            from database import get_db
            from community_analytics import peer_percentile

            db = get_db()
            _seed_grade_history(db, 1, "Biology", count=8)

            # Create 12 peer users with grades
            for uid in range(100, 112):
                db.execute(
                    "INSERT INTO users (id, name, email, password_hash, created_at) "
                    "VALUES (?, ?, ?, 'hash', ?)",
                    (uid, f"Peer {uid}", f"peer{uid}@test.com", datetime.now().isoformat()),
                )
                db.execute("INSERT OR IGNORE INTO gamification (user_id) VALUES (?)", (uid,))
                _seed_grade_history(db, uid, "Biology", count=6)

            result = peer_percentile(1, "Biology")
            assert "error" not in result
            assert "percentile" in result
            assert 0 <= result["percentile"] <= 100
            assert result["sample_size"] >= 10
            assert "avg_peer_score" in result
            assert "your_avg" in result

    def test_no_grades_for_subject(self, app):
        with app.app_context():
            from community_analytics import peer_percentile

            result = peer_percentile(1, "Nonexistent Subject")
            assert "error" in result


class TestInsightEndpoints:
    def test_predictions_endpoint(self, auth_client, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            _seed_grade_history(db, 1, "Biology", count=8)

        resp = auth_client.get("/api/insights/predictions")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "subject_predictions" in data

    def test_study_patterns_endpoint(self, auth_client, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            _seed_activity_log(db, 1, days=10)

        resp = auth_client.get("/api/insights/study-patterns")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "total_sessions" in data

    def test_peer_ranking_endpoint(self, auth_client):
        resp = auth_client.get("/api/insights/peer-ranking/Biology")
        assert resp.status_code == 200

    def test_share_and_view(self, auth_client, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            _seed_grade_history(db, 1, "Biology", count=8)
            _seed_activity_log(db, 1, days=5)

        # Create shared summary
        resp = auth_client.post("/api/insights/share", json={})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "token" in data

        # View shared summary (no auth required)
        client = app.test_client()
        resp = client.get(f"/share/{data['token']}")
        assert resp.status_code == 200

    def test_view_invalid_token(self, client):
        resp = client.get("/share/invalid-token-123")
        assert resp.status_code == 404

    def test_predictions_requires_auth(self, client):
        resp = client.get("/api/insights/predictions")
        assert resp.status_code in (302, 401)
