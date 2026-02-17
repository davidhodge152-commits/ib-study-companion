"""Tests for AI feedback system and AgentInteractionStoreDB."""

from __future__ import annotations

import json

import pytest


class TestAIFeedbackEndpoint:
    """Test POST /api/ai/feedback."""

    def test_feedback_thumbs_up(self, auth_client):
        resp = auth_client.post("/api/ai/feedback", json={
            "agent": "grading_agent",
            "feedback_type": "thumbs_up",
            "comment": "Great response!",
        })
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_feedback_thumbs_down(self, auth_client):
        resp = auth_client.post("/api/ai/feedback", json={
            "agent": "tutor_agent",
            "feedback_type": "thumbs_down",
            "comment": "Not helpful",
        })
        assert resp.status_code == 200

    def test_feedback_invalid_type(self, auth_client):
        resp = auth_client.post("/api/ai/feedback", json={
            "agent": "tutor_agent",
            "feedback_type": "invalid",
        })
        assert resp.status_code == 400

    def test_feedback_missing_agent(self, auth_client):
        resp = auth_client.post("/api/ai/feedback", json={
            "feedback_type": "thumbs_up",
        })
        assert resp.status_code == 400

    def test_feedback_requires_auth(self, client):
        resp = client.post("/api/ai/feedback", json={
            "agent": "grading_agent",
            "feedback_type": "thumbs_up",
        })
        # Should redirect to login
        assert resp.status_code in (302, 401)


class TestAgentInteractionStoreDB:
    """Test the AgentInteractionStoreDB class."""

    def test_log_and_recent(self, app):
        with app.app_context():
            from db_stores import AgentInteractionStoreDB

            iid = AgentInteractionStoreDB.log(
                user_id=1,
                intent="explain_concept",
                agent="tutor_agent",
                confidence=0.9,
                input_summary="What is photosynthesis?",
                response_summary="Photosynthesis is...",
                latency_ms=500,
                provider="gemini",
                model="gemini-2.0-flash",
                input_tokens_est=100,
                output_tokens_est=200,
                cost_estimate_usd=0.0001,
            )
            assert iid is not None

            recent = AgentInteractionStoreDB.recent(limit=5)
            assert len(recent) >= 1
            assert recent[0]["agent"] == "tutor_agent"
            assert recent[0]["provider"] == "gemini"

    def test_by_agent(self, app):
        with app.app_context():
            from db_stores import AgentInteractionStoreDB

            AgentInteractionStoreDB.log(
                user_id=1, intent="grade_answer", agent="grading_agent",
                confidence=0.85, input_summary="test", response_summary="test",
                latency_ms=300,
            )
            results = AgentInteractionStoreDB.by_agent("grading_agent")
            assert len(results) >= 1

    def test_cost_summary(self, app):
        with app.app_context():
            from db_stores import AgentInteractionStoreDB

            summary = AgentInteractionStoreDB.cost_summary(days=30)
            assert "total_cost" in summary
            assert "total_calls" in summary

    def test_feedback_stats(self, app):
        with app.app_context():
            from db_stores import AgentInteractionStoreDB

            stats = AgentInteractionStoreDB.feedback_stats()
            assert "stats" in stats


class TestMigrations3233:
    """Test that migrations 32 and 33 are applied."""

    def test_ai_feedback_table_exists(self, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            row = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='ai_feedback'"
            ).fetchone()
            assert row is not None

    def test_agent_interactions_has_cost_columns(self, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            cols = db.execute("PRAGMA table_info(agent_interactions)").fetchall()
            col_names = {c["name"] for c in cols}
            assert "provider" in col_names
            assert "model" in col_names
            assert "cost_estimate_usd" in col_names
            assert "cache_hit" in col_names
