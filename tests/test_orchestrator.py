"""Tests for the Compound AI orchestrator, agents, and STEM sandbox."""

from __future__ import annotations

import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


# ── Agent Response Dataclass ──────────────────────────────────────────

class TestAgentResponse:
    def test_basic_fields(self):
        from agents.base import AgentResponse

        r = AgentResponse(
            content="Hello",
            agent="tutor_agent",
            confidence=0.9,
        )
        assert r.content == "Hello"
        assert r.agent == "tutor_agent"
        assert r.confidence == 0.9
        assert r.metadata == {}
        assert r.follow_up is None

    def test_with_metadata(self):
        from agents.base import AgentResponse

        r = AgentResponse(
            content="Graded",
            agent="grading_agent",
            confidence=0.85,
            metadata={"mark_earned": 3, "mark_total": 4},
            follow_up="Want me to explain the criteria?",
        )
        assert r.metadata["mark_earned"] == 3
        assert r.follow_up is not None


# ── Intent Classification ─────────────────────────────────────────────

class TestIntentClassification:
    def _make_orchestrator(self, app):
        with app.app_context():
            from orchestrator import Orchestrator
            return Orchestrator(user_id=1)

    def test_grade_intent_from_context(self, app):
        orch = self._make_orchestrator(app)
        intent = orch.classify_intent(
            "Here is my answer",
            {"question": "Define osmosis", "answer": "Movement of water"},
        )
        assert intent == "grade_answer"

    def test_grade_intent_from_keywords(self, app):
        orch = self._make_orchestrator(app)
        assert orch.classify_intent("Please grade my answer") == "grade_answer"
        assert orch.classify_intent("Mark this for me") == "grade_answer"

    def test_coursework_intent(self, app):
        orch = self._make_orchestrator(app)
        assert orch.classify_intent("Review my IA please") == "review_coursework"
        assert orch.classify_intent("Can you give feedback on my EE?") == "review_coursework"

    def test_research_intent(self, app):
        orch = self._make_orchestrator(app)
        assert orch.classify_intent("Find examples of market failure") == "find_research"
        assert orch.classify_intent("I need a real-world example") == "find_research"

    def test_stem_intent(self, app):
        orch = self._make_orchestrator(app)
        intent = orch.classify_intent(
            "Calculate the derivative of x^2",
            {"subject": "Mathematics: AA"},
        )
        assert intent == "solve_stem"

    def test_explain_intent(self, app):
        orch = self._make_orchestrator(app)
        assert orch.classify_intent("Explain photosynthesis") == "explain_concept"
        assert orch.classify_intent("What is mitosis?") == "explain_concept"

    def test_help_question_intent(self, app):
        orch = self._make_orchestrator(app)
        intent = orch.classify_intent(
            "I'm stuck on this",
            {"question": "Explain the role of enzymes"},
        )
        assert intent == "help_question"

    def test_general_chat_fallback(self, app):
        orch = self._make_orchestrator(app)
        # Without an LLM key, ambiguous messages fall back to general_chat
        intent = orch.classify_intent("Hello there!")
        assert intent == "general_chat"


# ── Routing Logic ─────────────────────────────────────────────────────

class TestRouting:
    def test_grade_routes_to_grading_agent(self, app):
        with app.app_context():
            from orchestrator import Orchestrator

            orch = Orchestrator(user_id=1)

            # Mock the grading agent
            mock_agent = MagicMock()
            from agents.base import AgentResponse
            mock_agent.grade.return_value = AgentResponse(
                content="MARK: 3/4", agent="grading_agent", confidence=0.85,
                metadata={"mark_earned": 3, "mark_total": 4},
            )
            orch._agents["grading"] = mock_agent

            result = orch.route(
                "grade_answer", "Grade this",
                context={"question": "Define osmosis", "answer": "Water movement", "marks": 4},
            )
            assert result.agent == "grading_agent"
            mock_agent.grade.assert_called_once()

    def test_explain_routes_to_tutor_agent(self, app):
        with app.app_context():
            from orchestrator import Orchestrator

            orch = Orchestrator(user_id=1)

            mock_agent = MagicMock()
            from agents.base import AgentResponse
            mock_agent.tutor.return_value = AgentResponse(
                content="Let's explore this...", agent="tutor_agent", confidence=0.9,
            )
            orch._agents["tutor"] = mock_agent

            result = orch.route(
                "explain_concept", "Explain photosynthesis",
                context={"subject": "Biology", "topic": "Cell Biology"},
            )
            assert result.agent == "tutor_agent"
            mock_agent.tutor.assert_called_once()

    def test_stem_routes_to_stem_solver(self, app):
        with app.app_context():
            from orchestrator import Orchestrator

            orch = Orchestrator(user_id=1)

            mock_agent = MagicMock()
            from agents.base import AgentResponse
            mock_agent.solve.return_value = AgentResponse(
                content="The answer is 42", agent="stem_solver", confidence=0.85,
            )
            orch._agents["stem"] = mock_agent

            result = orch.route(
                "solve_stem", "Calculate 6*7",
                context={"subject": "Mathematics"},
            )
            assert result.agent == "stem_solver"

    def test_coursework_routes_to_coursework_agent(self, app):
        with app.app_context():
            from orchestrator import Orchestrator

            orch = Orchestrator(user_id=1)

            mock_agent = MagicMock()
            from agents.base import AgentResponse
            mock_agent.review.return_value = AgentResponse(
                content="Criterion A: 4/6", agent="coursework_agent", confidence=0.85,
            )
            orch._agents["coursework"] = mock_agent

            result = orch.route(
                "review_coursework", "Review my IA",
                context={"text": "My IA text here", "doc_type": "ia", "subject": "Biology"},
            )
            assert result.agent == "coursework_agent"

    def test_research_routes_to_research_agent(self, app):
        with app.app_context():
            from orchestrator import Orchestrator

            orch = Orchestrator(user_id=1)

            mock_agent = MagicMock()
            from agents.base import AgentResponse
            mock_agent.find_examples.return_value = AgentResponse(
                content="Example 1: ...", agent="research_agent", confidence=0.75,
            )
            orch._agents["research"] = mock_agent

            result = orch.route(
                "find_research", "Find examples of market failure",
                context={"topic": "Market failure", "subject": "Economics"},
            )
            assert result.agent == "research_agent"


# ── STEM Sandbox ──────────────────────────────────────────────────────

class TestSTEMSandbox:
    def test_sandbox_basic_math(self):
        from agents.stem_solver import STEMSolverAgent

        agent = STEMSolverAgent()
        result = agent._execute_sandbox("import math\nprint(math.sqrt(16))")
        assert result is not None
        assert "4" in result

    def test_sandbox_timeout(self):
        from agents.stem_solver import STEMSolverAgent

        agent = STEMSolverAgent()
        result = agent._execute_sandbox(
            "import time\ntime.sleep(10)\nprint('done')",
            timeout=1,
        )
        assert result is None

    def test_sandbox_blocks_file_access(self):
        from agents.stem_solver import STEMSolverAgent

        agent = STEMSolverAgent()
        result = agent._execute_sandbox("open('/etc/passwd').read()")
        assert result is None

    def test_sandbox_blocks_subprocess(self):
        from agents.stem_solver import STEMSolverAgent

        agent = STEMSolverAgent()
        result = agent._execute_sandbox("import subprocess; subprocess.run(['ls'])")
        assert result is None

    def test_sandbox_blocks_os_system(self):
        from agents.stem_solver import STEMSolverAgent

        agent = STEMSolverAgent()
        result = agent._execute_sandbox("import os; os.system('ls')")
        assert result is None

    def test_sandbox_blocks_network(self):
        from agents.stem_solver import STEMSolverAgent

        agent = STEMSolverAgent()
        result = agent._execute_sandbox("import socket; socket.socket()")
        assert result is None

    def test_sandbox_blocks_import_tricks(self):
        from agents.stem_solver import STEMSolverAgent

        agent = STEMSolverAgent()
        result = agent._execute_sandbox("__import__('os').system('ls')")
        assert result is None

    def test_sandbox_allows_numpy(self):
        from agents.stem_solver import STEMSolverAgent

        agent = STEMSolverAgent()
        result = agent._execute_sandbox(
            "import numpy as np\nprint(np.array([1,2,3]).sum())"
        )
        # May be None if numpy not installed, but should not crash
        if result is not None:
            assert "6" in result

    def test_code_extraction(self):
        from agents.stem_solver import STEMSolverAgent

        agent = STEMSolverAgent()

        # Test with code block
        code = agent._extract_code("```python\nprint(42)\n```")
        assert code == "print(42)"

        # Test with generic code block
        code = agent._extract_code("```\nprint(42)\n```")
        assert code == "print(42)"

        # Test with raw code
        code = agent._extract_code("print(42)")
        assert "print(42)" in code


# ── Graceful Fallback ─────────────────────────────────────────────────

class TestGracefulFallback:
    def test_tutor_without_keys(self, app):
        """TutorAgent should gracefully handle missing API keys."""
        with app.app_context():
            from agents.tutor_agent import TutorAgent

            agent = TutorAgent()
            # Force provider to none to simulate missing keys
            agent._provider = "none"
            agent._claude_client = None
            agent._gemini_model = None

            result = agent.tutor(
                messages=[{"role": "user", "content": "Hello"}],
                subject="Biology",
                topic="Cells",
            )
            assert result.confidence == 0.0
            assert "API key" in result.content

    def test_grading_without_keys(self, app):
        """GradingAgent should gracefully handle missing API keys."""
        with app.app_context():
            from agents.grading_agent import GradingAgent

            agent = GradingAgent()
            # Force model to None to simulate missing key
            agent.model = None

            result = agent.grade(
                question="Define osmosis",
                answer="Water movement",
                subject="biology",
                marks=4,
            )
            assert result.confidence == 0.0

    def test_stem_without_keys(self, app):
        """STEMSolverAgent should gracefully handle missing API keys."""
        with app.app_context():
            from agents.stem_solver import STEMSolverAgent

            agent = STEMSolverAgent()
            agent._provider = "none"
            agent._openai_client = None
            agent._gemini_model = None

            result = agent.solve("What is 2+2?")
            assert result.confidence == 0.0

    def test_coursework_without_keys(self, app):
        """CourseworkAgent should gracefully handle missing API keys."""
        with app.app_context():
            from agents.coursework_agent import CourseworkAgent

            agent = CourseworkAgent()
            agent._provider = "none"
            agent._claude_client = None
            agent._gemini_model = None

            result = agent.review("My IA text", "ia", "Biology")
            assert result.confidence == 0.0

    def test_research_without_keys(self, app):
        """ResearchAgent should gracefully handle missing API keys."""
        with app.app_context():
            from agents.research_agent import ResearchAgent

            agent = ResearchAgent()
            agent._model = None

            result = agent.find_examples("Market failure", "Economics")
            assert result.confidence == 0.0


# ── Agent Interaction Logging ─────────────────────────────────────────

class TestAgentInteractionLogging:
    def test_interaction_logged(self, app):
        with app.app_context():
            from orchestrator import Orchestrator
            from agents.base import AgentResponse
            from database import get_db

            orch = Orchestrator(user_id=1)

            # Mock a tutor agent
            mock_agent = MagicMock()
            mock_agent.tutor.return_value = AgentResponse(
                content="Let me help...", agent="tutor_agent", confidence=0.9,
            )
            orch._agents["tutor"] = mock_agent

            orch.route("explain_concept", "Explain osmosis",
                       context={"subject": "Biology"})

            db = get_db()
            rows = db.execute(
                "SELECT * FROM agent_interactions WHERE user_id = 1"
            ).fetchall()
            assert len(rows) >= 1
            row = rows[0]
            assert row["intent"] == "explain_concept"
            assert row["agent"] == "tutor_agent"
            assert row["confidence"] == 0.9


# ── Unified Chat Endpoint ─────────────────────────────────────────────

class TestAIChatEndpoint:
    def test_chat_requires_auth(self, client):
        resp = client.post("/api/ai/chat", json={"message": "hello"})
        assert resp.status_code in (302, 401)

    def test_chat_requires_message(self, auth_client):
        resp = auth_client.post("/api/ai/chat", json={})
        assert resp.status_code == 400

    def test_chat_returns_response(self, auth_client):
        from agents.base import AgentResponse

        mock_response = AgentResponse(
            content="Hello! How can I help?",
            agent="tutor_agent",
            confidence=0.9,
            metadata={"provider": "mock"},
        )

        with patch("orchestrator.Orchestrator.classify_intent", return_value="general_chat"), \
             patch("orchestrator.Orchestrator.route", return_value=mock_response):
            resp = auth_client.post("/api/ai/chat", json={
                "message": "Hello",
                "context": {"subject": "Biology"},
            })
            assert resp.status_code == 200
            data = resp.get_json()
            assert "response" in data
            assert data["agent"] == "tutor_agent"
            assert data["intent"] == "general_chat"


# ── Migration Test ────────────────────────────────────────────────────

class TestMigration10:
    def test_agent_interactions_table_exists(self, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            # Should not raise
            db.execute("SELECT * FROM agent_interactions LIMIT 1")

    def test_topic_prerequisites_table_exists(self, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute("SELECT * FROM topic_prerequisites LIMIT 1")

    def test_student_memory_table_exists(self, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute("SELECT * FROM student_memory LIMIT 1")
