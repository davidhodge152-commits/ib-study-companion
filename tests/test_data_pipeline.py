"""Tests for data pipeline: daily aggregation, anonymized export, seed data, scheduler."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest


def _seed_todays_data(db):
    """Insert grades and activity for today."""
    today = datetime.now().strftime("%Y-%m-%d")
    ts = datetime.now().isoformat()
    for i in range(5):
        db.execute(
            "INSERT INTO grades (user_id, subject, subject_display, level, "
            "command_term, grade, percentage, mark_earned, mark_total, "
            "strengths, improvements, examiner_tip, topic, timestamp) "
            "VALUES (1, 'biology', 'Biology', 'HL', 'Explain', ?, ?, 3, 4, "
            "'[]', '[]', '', 'Topic 1', ?)",
            (4 + i, (4 + i) * 14, ts),
        )
    db.execute(
        "INSERT INTO activity_log (user_id, date, subject, questions_attempted, "
        "duration_minutes, timestamp) VALUES (1, ?, 'Biology', 5, 30, ?)",
        (today, ts),
    )
    db.commit()


class TestDailyAggregation:
    def test_aggregate_returns_stats(self, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            _seed_todays_data(db)

        from data_pipeline import aggregate_daily_analytics
        result = aggregate_daily_analytics(app)

        assert result["date"] == datetime.now().strftime("%Y-%m-%d")
        assert result["questions_graded"] >= 5
        assert result["active_users"] >= 1
        assert result["avg_score"] > 0

    def test_aggregate_upserts(self, app):
        """Running twice should update, not duplicate."""
        with app.app_context():
            from database import get_db
            db = get_db()
            _seed_todays_data(db)

        from data_pipeline import aggregate_daily_analytics
        aggregate_daily_analytics(app)
        aggregate_daily_analytics(app)

        with app.app_context():
            from database import get_db
            db = get_db()
            rows = db.execute(
                "SELECT * FROM daily_aggregates WHERE date = ? AND metric = 'active_users'",
                (datetime.now().strftime("%Y-%m-%d"),),
            ).fetchall()
            assert len(rows) == 1

    def test_aggregate_empty_day(self, app):
        from data_pipeline import aggregate_daily_analytics
        result = aggregate_daily_analytics(app)
        assert result["questions_graded"] == 0
        assert result["active_users"] == 0


class TestAnonymizedExport:
    def test_export_structure(self, app):
        from data_pipeline import export_anonymized_analytics
        result = export_anonymized_analytics(app)

        assert "export_date" in result
        assert "grade_distribution" in result
        assert "daily_activity" in result
        assert "agent_usage" in result
        assert "conversion_funnel" in result
        assert "user_aggregates" in result

        funnel = result["conversion_funnel"]
        assert "registered" in funnel
        assert "onboarded" in funnel
        assert "has_grades" in funnel
        assert "active_this_week" in funnel

    def test_export_hashes_user_ids(self, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            _seed_todays_data(db)

        from data_pipeline import export_anonymized_analytics
        result = export_anonymized_analytics(app)

        for entry in result["user_aggregates"]:
            assert "anon_id" in entry
            assert len(entry["anon_id"]) == 12  # SHA256 truncated
            assert "user_id" not in entry


class TestSeedDemoData:
    def test_seed_creates_data(self, app):
        with app.app_context():
            from database import get_db
            from seed_demo_data import seed, clear_demo

            db = get_db()
            result = seed(db)

            assert result["students_created"] == 5
            assert result["grades_seeded"] > 50
            assert result["class_id"] == 100

            # Verify students exist
            count = db.execute(
                "SELECT COUNT(*) as c FROM users WHERE id >= 200 AND id < 210"
            ).fetchone()["c"]
            assert count >= 5

            # Clean up
            clear_demo(db)
            count = db.execute(
                "SELECT COUNT(*) as c FROM users WHERE id >= 200 AND id < 210"
            ).fetchone()["c"]
            assert count == 0


class TestAdminExportEndpoint:
    def test_export_requires_teacher(self, client):
        resp = client.get("/api/admin/analytics-export")
        assert resp.status_code in (302, 401)

    def test_export_returns_data(self, teacher_client):
        resp = teacher_client.get("/api/admin/analytics-export")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "conversion_funnel" in data


class TestMigration36:
    def test_daily_aggregates_table_exists(self, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            row = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='daily_aggregates'"
            ).fetchone()
            assert row is not None
