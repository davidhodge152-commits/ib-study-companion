"""Tests for the Syllabus Knowledge Graph and Bayesian Knowledge Tracing."""

from __future__ import annotations

import pytest
from datetime import datetime


class TestMasteryComputation:
    def test_unknown_state(self):
        from adaptive import compute_mastery

        assert compute_mastery(0.0, 1.0, 0, 0.0) == "unknown"

    def test_learning_low_theta(self):
        from adaptive import compute_mastery

        assert compute_mastery(-0.5, 0.3, 3, 0.3) == "learning"

    def test_learning_high_uncertainty(self):
        from adaptive import compute_mastery

        assert compute_mastery(0.2, 0.7, 2, 0.5) == "learning"

    def test_partial_state(self):
        from adaptive import compute_mastery

        assert compute_mastery(0.2, 0.3, 3, 0.6) == "partial"

    def test_mastered_state(self):
        from adaptive import compute_mastery

        assert compute_mastery(0.8, 0.2, 10, 0.9) == "mastered"

    def test_not_mastered_insufficient_attempts(self):
        from adaptive import compute_mastery

        # High theta but only 3 attempts — still partial
        assert compute_mastery(0.8, 0.2, 3, 0.9) == "partial"

    def test_not_mastered_high_uncertainty(self):
        from adaptive import compute_mastery

        # High theta but high uncertainty — still learning
        assert compute_mastery(0.8, 0.6, 10, 0.9) == "learning"

    def test_boundary_partial_to_mastered(self):
        from adaptive import compute_mastery

        # Exactly at mastery threshold
        assert compute_mastery(0.5, 0.3, 5, 0.7) == "partial"
        # Just above threshold
        assert compute_mastery(0.51, 0.29, 5, 0.7) == "mastered"


class TestKnowledgeGraph:
    def _seed_prerequisites(self, db):
        """Insert test prerequisite edges."""
        edges = [
            ("Biology", "bio_2", "bio_1", 1.0),
            ("Biology", "bio_3", "bio_2", 1.0),
            ("Biology", "bio_5", "bio_3", 1.0),
        ]
        for subject, topic, requires, strength in edges:
            db.execute(
                "INSERT OR IGNORE INTO topic_prerequisites "
                "(subject, topic_id, requires_topic_id, strength) "
                "VALUES (?, ?, ?, ?)",
                (subject, topic, requires, strength),
            )
        db.commit()

    def test_get_prerequisites(self, app):
        with app.app_context():
            from database import get_db
            from knowledge_graph import SyllabusGraph

            db = get_db()
            self._seed_prerequisites(db)

            graph = SyllabusGraph("Biology")
            prereqs = graph.get_prerequisites("bio_2")
            assert "bio_1" in prereqs

    def test_get_dependents(self, app):
        with app.app_context():
            from database import get_db
            from knowledge_graph import SyllabusGraph

            db = get_db()
            self._seed_prerequisites(db)

            graph = SyllabusGraph("Biology")
            deps = graph.get_dependents("bio_1")
            assert "bio_2" in deps

    def test_chain_prerequisites(self, app):
        with app.app_context():
            from database import get_db
            from knowledge_graph import SyllabusGraph

            db = get_db()
            self._seed_prerequisites(db)

            graph = SyllabusGraph("Biology")
            # bio_3 requires bio_2, which requires bio_1
            prereqs = graph.get_prerequisites("bio_3")
            assert "bio_2" in prereqs
            # bio_2's prereqs
            prereqs2 = graph.get_prerequisites("bio_2")
            assert "bio_1" in prereqs2

    def test_mastery_map_all_unknown(self, app):
        with app.app_context():
            from knowledge_graph import SyllabusGraph

            graph = SyllabusGraph("Biology")
            mastery = graph.get_mastery_map(user_id=1)
            # Should have entries for all Biology topics
            assert len(mastery) > 0
            # All should be unknown (no ability data seeded)
            for topic_id, info in mastery.items():
                assert info["state"] == "unknown"

    def test_mastery_map_with_ability_data(self, app):
        with app.app_context():
            from database import get_db
            from knowledge_graph import SyllabusGraph

            db = get_db()
            self._seed_prerequisites(db)

            # Seed ability data for bio_1 (mastered)
            db.execute(
                "INSERT OR REPLACE INTO student_ability "
                "(user_id, subject, topic, theta, uncertainty, attempts, mastery_state, last_correct_ratio) "
                "VALUES (1, 'Biology', 'Cell Biology', 0.8, 0.2, 10, 'mastered', 0.9)",
            )
            db.commit()

            graph = SyllabusGraph("Biology")
            mastery = graph.get_mastery_map(user_id=1)

            assert mastery["bio_1"]["state"] == "mastered"
            # bio_2 should have prerequisites met (bio_1 is mastered)
            assert mastery["bio_2"]["prerequisites_met"] is True

    def test_recommended_topics(self, app):
        with app.app_context():
            from database import get_db
            from knowledge_graph import SyllabusGraph

            db = get_db()
            self._seed_prerequisites(db)

            # Seed: bio_1 mastered, bio_2 partial
            db.execute(
                "INSERT OR REPLACE INTO student_ability "
                "(user_id, subject, topic, theta, uncertainty, attempts, mastery_state, last_correct_ratio) "
                "VALUES (1, 'Biology', 'Cell Biology', 0.8, 0.2, 10, 'mastered', 0.9)",
            )
            db.execute(
                "INSERT OR REPLACE INTO student_ability "
                "(user_id, subject, topic, theta, uncertainty, attempts, mastery_state, last_correct_ratio) "
                "VALUES (1, 'Biology', 'Molecular Biology', 0.1, 0.4, 3, 'partial', 0.5)",
            )
            db.commit()

            graph = SyllabusGraph("Biology")
            recommended = graph.get_recommended_next(user_id=1, limit=3)

            # Should recommend topics that aren't mastered
            assert len(recommended) > 0
            for r in recommended:
                assert r["state"] != "mastered"

    def test_learning_path(self, app):
        with app.app_context():
            from database import get_db
            from knowledge_graph import SyllabusGraph

            db = get_db()
            self._seed_prerequisites(db)

            graph = SyllabusGraph("Biology")
            path = graph.get_learning_path("bio_3", user_id=1)

            # Path should include prerequisites first
            assert len(path) > 0
            # bio_1 or bio_2 should appear before bio_3
            if "bio_3" in path and "bio_1" in path:
                assert path.index("bio_1") < path.index("bio_3")


class TestAdaptiveMastery:
    def test_update_theta_returns_mastery(self, app):
        with app.app_context():
            from adaptive import update_theta

            result = update_theta(
                user_id=1,
                subject="biology",
                topic="Cell Biology",
                difficulty=1.0,
                correct_ratio=0.8,
            )
            assert "mastery_state" in result
            assert result["mastery_state"] in ("unknown", "learning", "partial", "mastered")

    def test_mastery_progresses(self, app):
        with app.app_context():
            from adaptive import update_theta

            # Simulate many correct answers — need ~15 to get uncertainty below 0.5
            # uncertainty = 1.0 * 0.95^n; 0.95^14 ≈ 0.488, so 14+ iterations
            for _ in range(20):
                result = update_theta(
                    user_id=1,
                    subject="biology",
                    topic="Mastery Test Topic",
                    difficulty=0.5,
                    correct_ratio=1.0,
                )

            # After many correct answers, uncertainty should be low enough
            assert result["mastery_state"] in ("partial", "mastered")
            assert result["attempts"] >= 20


class TestSeedPrerequisites:
    def test_seed_creates_edges(self, app):
        with app.app_context():
            from seed_prerequisites import PREREQUISITES
            from database import get_db

            db = get_db()

            # Insert a few manually
            for subject, topic_id, requires, strength in PREREQUISITES[:5]:
                db.execute(
                    "INSERT OR IGNORE INTO topic_prerequisites "
                    "(subject, topic_id, requires_topic_id, strength) "
                    "VALUES (?, ?, ?, ?)",
                    (subject, topic_id, requires, strength),
                )
            db.commit()

            rows = db.execute("SELECT COUNT(*) as c FROM topic_prerequisites").fetchone()
            assert rows["c"] >= 5
