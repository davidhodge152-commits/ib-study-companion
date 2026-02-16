"""Tests for database.py — schema creation, foreign keys, basic operations."""

import json
import pytest
from database import get_db, init_db


class TestSchema:
    """Verify all tables are created correctly."""

    def test_tables_exist(self, app):
        with app.app_context():
            db = get_db()
            tables = [r["name"] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()]
            expected = [
                "activity_log", "cas_reflections", "extended_essays", "flashcards",
                "gamification", "grade_history", "grades", "internal_assessments",
                "milestones", "misconceptions", "mock_reports", "notifications",
                "parent_config", "review_schedule", "schema_version", "shared_questions",
                "study_plans", "tok_progress", "topic_progress", "uploads",
                "user_subjects", "users", "writing_profiles",
            ]
            for t in expected:
                assert t in tables, f"Table {t} not found"

    def test_wal_mode(self, app):
        with app.app_context():
            db = get_db()
            mode = db.execute("PRAGMA journal_mode").fetchone()[0]
            assert mode == "wal"

    def test_foreign_keys_enabled(self, app):
        with app.app_context():
            db = get_db()
            fk = db.execute("PRAGMA foreign_keys").fetchone()[0]
            assert fk == 1

    def test_seed_user_exists(self, db):
        row = db.execute("SELECT * FROM users WHERE id=1").fetchone()
        assert row is not None
        assert row["name"] == "Test Student"

    def test_seed_subjects_exist(self, db):
        rows = db.execute("SELECT * FROM user_subjects WHERE user_id=1").fetchall()
        assert len(rows) == 3
        names = {r["name"] for r in rows}
        assert "Biology" in names
        assert "Chemistry" in names

    def test_gamification_row_exists(self, db):
        row = db.execute("SELECT * FROM gamification WHERE user_id=1").fetchone()
        assert row is not None
        assert row["total_xp"] == 0

    def test_foreign_key_cascade(self, app):
        """Deleting a user should cascade to related tables."""
        with app.app_context():
            db = get_db()
            # Add data linked to user 1
            db.execute(
                "INSERT INTO grades (user_id, subject, subject_display, grade, percentage, mark_earned, mark_total) "
                "VALUES (1, 'bio', 'Biology', 5, 65, 3, 4)"
            )
            db.commit()
            assert db.execute("SELECT COUNT(*) as c FROM grades WHERE user_id=1").fetchone()["c"] > 0

            # Delete user
            db.execute("DELETE FROM users WHERE id=1")
            db.commit()
            assert db.execute("SELECT COUNT(*) as c FROM grades WHERE user_id=1").fetchone()["c"] == 0
            assert db.execute("SELECT COUNT(*) as c FROM user_subjects WHERE user_id=1").fetchone()["c"] == 0
