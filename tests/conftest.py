"""
Test fixtures for IB Study Companion.

Provides app, client, auth_client, and db fixtures with file-based SQLite.
Gemini is mocked globally to avoid API calls during tests.
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session", autouse=True)
def mock_gemini():
    """Mock Google Generative AI globally to prevent API calls."""
    mock_model = MagicMock()
    mock_model.generate_content.return_value = MagicMock(
        text="MARK: 3/4\nGRADE: 5\nPERCENTAGE: 75%\n\n"
             "STRENGTHS:\n- Good use of terminology\n- Clear structure\n\n"
             "IMPROVEMENTS:\n- Needs more specific examples\n- Could improve evaluation\n\n"
             "EXAMINER_TIP:\nAlways define key terms before using them.\n\n"
             "FULL_COMMENTARY:\nA solid attempt that demonstrates understanding.\n\n"
             "MODEL_ANSWER:\nA model answer would include specific examples."
    )

    with patch.dict("sys.modules", {
        "google.generativeai": MagicMock(),
    }):
        yield mock_model


@pytest.fixture
def app(tmp_path):
    """Create app with file-based SQLite for testing."""
    from app import create_app

    db_file = str(tmp_path / "test.db")
    app = create_app({
        "TESTING": True,
        "DATABASE": db_file,
        "SECRET_KEY": "test-secret-key",
        "WTF_CSRF_ENABLED": False,
    })

    with app.app_context():
        from database import init_db, run_migrations, get_db

        init_db()
        run_migrations()

        # Seed test user
        db = get_db()
        db.execute(
            "INSERT INTO users (id, name, email, password_hash, exam_session, target_total_points, created_at) "
            "VALUES (1, 'Test Student', 'test@example.com', ?, 'May 2026', 38, ?)",
            ("pbkdf2:sha256:600000$test$hash", datetime.now().isoformat()),
        )
        db.execute("INSERT INTO user_subjects (user_id, name, level, target_grade) VALUES (1, 'Biology', 'HL', 6)")
        db.execute("INSERT INTO user_subjects (user_id, name, level, target_grade) VALUES (1, 'Chemistry', 'SL', 5)")
        db.execute("INSERT INTO user_subjects (user_id, name, level, target_grade) VALUES (1, 'Mathematics: AA', 'HL', 7)")
        db.execute("INSERT OR IGNORE INTO gamification (user_id) VALUES (1)")
        db.commit()

        yield app


@pytest.fixture
def client(app):
    """Unauthenticated test client."""
    return app.test_client()


@pytest.fixture
def auth_client(app):
    """Authenticated test client (logged in as test user)."""
    from werkzeug.security import generate_password_hash
    from database import get_db

    with app.app_context():
        db = get_db()
        db.execute(
            "UPDATE users SET password_hash = ? WHERE id = 1",
            (generate_password_hash("testpass123"),),
        )
        db.commit()

    client = app.test_client()
    with client:
        client.post("/login", data={
            "email": "test@example.com",
            "password": "testpass123",
        }, follow_redirects=True)
        yield client


@pytest.fixture
def teacher_client(app):
    """Authenticated test client logged in as a teacher with a class and student."""
    from werkzeug.security import generate_password_hash
    from database import get_db

    with app.app_context():
        db = get_db()
        # Create a school
        db.execute(
            "INSERT INTO schools (id, name, code, created_at) VALUES (1, 'Test School', 'SCHOOL1', '2026-01-01')"
        )
        # Create teacher user
        db.execute(
            "INSERT INTO users (id, name, email, password_hash, role, school_id, created_at) "
            "VALUES (2, 'Test Teacher', 'teacher@test.com', ?, 'teacher', 1, '2026-01-01')",
            (generate_password_hash("TeacherPass1"),),
        )
        db.execute("INSERT OR IGNORE INTO gamification (user_id) VALUES (2)")
        # Create a class owned by the teacher
        db.execute(
            "INSERT INTO classes (id, school_id, teacher_id, name, subject, level, join_code, created_at) "
            "VALUES (1, 1, 2, 'Biology HL', 'Biology', 'HL', 'TESTJOIN', '2026-01-01')"
        )
        # Add the test student (user 1) to the class
        db.execute(
            "INSERT INTO class_members (class_id, user_id, joined_at) VALUES (1, 1, '2026-01-01')"
        )
        db.commit()

    client = app.test_client()
    with client:
        client.post("/login", data={
            "email": "teacher@test.com",
            "password": "TeacherPass1",
        }, follow_redirects=True)
        yield client


@pytest.fixture
def db(app):
    """Direct database access for store tests."""
    with app.app_context():
        from database import get_db
        yield get_db()


@pytest.fixture
def seeded_grades(app):
    """Seed some grade data for testing."""
    with app.app_context():
        from database import get_db
        db = get_db()
        grades = [
            (1, "biology", "Biology", "HL", "Explain", 5, 68, 3, 4,
             '["Good terminology"]', '["Needs examples"]', "Define terms first", "Topic 1",
             "2026-01-15T10:00:00"),
            (1, "biology", "Biology", "HL", "Evaluate", 6, 75, 6, 8,
             '["Balanced argument"]', '["Deeper analysis needed"]', "Consider both sides", "Topic 2",
             "2026-01-20T10:00:00"),
            (1, "chemistry", "Chemistry", "SL", "Define", 7, 90, 2, 2,
             '["Precise definition"]', '[]', "Good work", "Topic 3",
             "2026-02-01T10:00:00"),
        ]
        for g in grades:
            db.execute(
                "INSERT INTO grades (user_id, subject, subject_display, level, command_term, "
                "grade, percentage, mark_earned, mark_total, strengths, improvements, "
                "examiner_tip, topic, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                g,
            )
        db.commit()
