"""Tests for the Semantic Student Memory system."""

from __future__ import annotations

import pytest
from datetime import datetime


class TestStudentMemory:
    def test_remember_and_recall(self, app):
        with app.app_context():
            from memory import StudentMemory

            mem = StudentMemory(user_id=1)
            mem.remember("interest", "hobby_chess", "Student plays chess competitively")
            mem.remember("preference", "step_by_step", "Prefers step-by-step explanations")

            memories = mem.recall()
            assert len(memories) >= 2

            interests = mem.recall("interest")
            assert len(interests) >= 1
            assert any("chess" in m["value"] for m in interests)

    def test_remember_upsert(self, app):
        with app.app_context():
            from memory import StudentMemory

            mem = StudentMemory(user_id=1)
            mem.remember("interest", "sport", "Likes football")
            mem.remember("interest", "sport", "Loves Formula 1 racing")

            interests = mem.recall("interest")
            sport_memories = [m for m in interests if m["key"] == "sport"]
            assert len(sport_memories) == 1
            assert "Formula 1" in sport_memories[0]["value"]

    def test_forget(self, app):
        with app.app_context():
            from memory import StudentMemory

            mem = StudentMemory(user_id=1)
            mem.remember("struggle", "plus_c", "Forgets +C in integration")
            mem.forget("struggle", "plus_c")

            struggles = mem.recall("struggle")
            assert not any(m["key"] == "plus_c" for m in struggles)

    def test_invalid_memory_type_ignored(self, app):
        with app.app_context():
            from memory import StudentMemory

            mem = StudentMemory(user_id=1)
            mem.remember("invalid_type", "key", "value")

            memories = mem.recall()
            assert not any(m["memory_type"] == "invalid_type" for m in memories)

    def test_recall_for_prompt_empty(self, app):
        with app.app_context():
            from memory import StudentMemory

            mem = StudentMemory(user_id=999)  # No memories for this user
            prompt = mem.recall_for_prompt()
            assert prompt == ""

    def test_recall_for_prompt_formatted(self, app):
        with app.app_context():
            from memory import StudentMemory

            mem = StudentMemory(user_id=1)
            mem.remember("interest", "hobby_f1", "Loves Formula 1 racing")
            mem.remember("preference", "visual", "Prefers visual explanations with diagrams")
            mem.remember("struggle", "integration_c", "Forgets +C in integration")

            prompt = mem.recall_for_prompt("Mathematics")
            assert "STUDENT MEMORY:" in prompt
            assert "Formula 1" in prompt
            assert "visual" in prompt
            assert "integration" in prompt

    def test_multiple_users_isolated(self, app):
        with app.app_context():
            from database import get_db

            # Create a second user
            db = get_db()
            db.execute(
                "INSERT OR IGNORE INTO users (id, name, created_at) VALUES (2, 'User 2', ?)",
                (datetime.now().isoformat(),),
            )
            db.commit()

            from memory import StudentMemory

            mem1 = StudentMemory(user_id=1)
            mem2 = StudentMemory(user_id=2)

            mem1.remember("interest", "music", "Plays guitar")
            mem2.remember("interest", "art", "Paints watercolors")

            assert any("guitar" in m["value"] for m in mem1.recall())
            assert not any("watercolors" in m["value"] for m in mem1.recall())

            assert any("watercolors" in m["value"] for m in mem2.recall())
            assert not any("guitar" in m["value"] for m in mem2.recall())

    def test_confidence_stored(self, app):
        with app.app_context():
            from memory import StudentMemory

            mem = StudentMemory(user_id=1)
            mem.remember("learning_style", "visual", "Prefers diagrams", confidence=0.7)

            memories = mem.recall("learning_style")
            visual = [m for m in memories if m["key"] == "visual"]
            assert len(visual) == 1
            assert visual[0]["confidence"] == 0.7


class TestAutoExtract:
    def test_auto_extract_no_key(self, app):
        """auto_extract should handle missing API key gracefully."""
        with app.app_context():
            from memory import StudentMemory
            import os

            with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
                "os.environ", {}, clear=True
            ):
                mem = StudentMemory(user_id=1)
                result = mem.auto_extract([
                    {"role": "user", "content": "I love chess"},
                    {"role": "assistant", "content": "That's great!"},
                ])
                assert result == []

    def test_auto_extract_short_conversation(self, app):
        """auto_extract should skip very short conversations."""
        with app.app_context():
            from memory import StudentMemory

            mem = StudentMemory(user_id=1)
            result = mem.auto_extract([
                {"role": "user", "content": "Hi"},
            ])
            assert result == []


class TestMemoryMigration:
    def test_student_memory_table_schema(self, app):
        with app.app_context():
            from database import get_db

            db = get_db()
            # Verify table exists and has expected columns
            row = db.execute(
                "PRAGMA table_info(student_memory)"
            ).fetchall()
            columns = {r["name"] for r in row}
            assert "user_id" in columns
            assert "memory_type" in columns
            assert "key" in columns
            assert "value" in columns
            assert "confidence" in columns
            assert "source" in columns

    def test_unique_constraint(self, app):
        with app.app_context():
            from memory import StudentMemory

            mem = StudentMemory(user_id=1)
            # Insert twice with same key — should upsert, not duplicate
            mem.remember("interest", "test_key", "value1")
            mem.remember("interest", "test_key", "value2")

            from database import get_db
            db = get_db()
            count = db.execute(
                "SELECT COUNT(*) as c FROM student_memory "
                "WHERE user_id = 1 AND memory_type = 'interest' AND key = 'test_key'"
            ).fetchone()["c"]
            assert count == 1
