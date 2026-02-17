"""Tests for the 6 category-killing differentiator features.

Covers: Vision Agent, Oral Exam Agent, Coursework IDE Agent,
TOK Synthesis Agent, Question Gen Agent, Executive Agent.
Tests intent classification, routing, agent methods, endpoints, and migrations.
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, date, timedelta


# ══════════════════════════════════════════════════════════════════════
# ─── Migration Tests (M14–M17) ──────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════

class TestMigrations14to17:
    """Verify all new tables exist after migrations."""

    def test_handwriting_analyses_table(self, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute("SELECT id, user_id, subject, question, image_hash, "
                       "extracted_steps, ecf_breakdown, total_marks, earned_marks, "
                       "ecf_marks, error_line, created_at FROM handwriting_analyses LIMIT 1")

    def test_oral_sessions_table(self, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute("SELECT id, user_id, subject, level, text_title, "
                       "global_issue, phase, started_at, completed_at, "
                       "transcript, examiner_questions, student_claims, "
                       "criterion_scores, total_score, feedback "
                       "FROM oral_sessions LIMIT 1")

    def test_coursework_sessions_table(self, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute("SELECT id, user_id, doc_type, subject, title, "
                       "current_phase, created_at, updated_at "
                       "FROM coursework_sessions LIMIT 1")

    def test_coursework_drafts_table(self, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute("SELECT id, session_id, version, text_content, "
                       "word_count, criterion_scores, feedback, created_at "
                       "FROM coursework_drafts LIMIT 1")

    def test_data_analyses_table(self, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute("SELECT id, session_id, raw_data, analysis_result, "
                       "graphs, statistical_tests, created_at "
                       "FROM data_analyses LIMIT 1")

    def test_smart_study_plans_table(self, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute("SELECT id, user_id, generated_at, days_ahead, "
                       "daily_allocations, total_study_minutes, "
                       "priority_subjects, burnout_risk "
                       "FROM smart_study_plans LIMIT 1")

    def test_study_deadlines_table(self, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute("SELECT id, user_id, title, subject, deadline_type, "
                       "due_date, importance, completed, created_at "
                       "FROM study_deadlines LIMIT 1")


# ══════════════════════════════════════════════════════════════════════
# ─── Intent Classification for New Intents ───────────────────────────
# ══════════════════════════════════════════════════════════════════════

class TestNewIntentClassification:
    def _make_orchestrator(self, app):
        with app.app_context():
            from orchestrator import Orchestrator
            return Orchestrator(user_id=1)

    def test_handwriting_intent(self, app):
        orch = self._make_orchestrator(app)
        assert orch.classify_intent("Check my working please") == "analyze_handwriting"
        assert orch.classify_intent("Here's a photo of my work") == "analyze_handwriting"

    def test_oral_intent(self, app):
        orch = self._make_orchestrator(app)
        assert orch.classify_intent("I want to practice oral exam") == "practice_oral"
        assert orch.classify_intent("IO practice for English") == "practice_oral"
        assert orch.classify_intent("individual oral preparation") == "practice_oral"

    def test_feasibility_intent(self, app):
        orch = self._make_orchestrator(app)
        assert orch.classify_intent("Is this a good topic for my IA?") == "check_feasibility"
        assert orch.classify_intent("Check feasibility of my research question") == "check_feasibility"

    def test_data_analysis_intent(self, app):
        orch = self._make_orchestrator(app)
        assert orch.classify_intent("Can you analyze my data?") == "analyze_data"
        assert orch.classify_intent("Run statistics on my results") == "analyze_data"
        assert orch.classify_intent("I need a chi-squared test") == "analyze_data"

    def test_tok_synthesis_intent(self, app):
        orch = self._make_orchestrator(app)
        assert orch.classify_intent("How do I connect subjects for my TOK essay?") == "tok_synthesis"
        assert orch.classify_intent("Areas of knowledge in Biology vs History") == "tok_synthesis"
        assert orch.classify_intent("Ways of knowing comparison") == "tok_synthesis"

    def test_question_gen_intent(self, app):
        orch = self._make_orchestrator(app)
        assert orch.classify_intent("Give me questions on calculus") == "generate_questions"
        assert orch.classify_intent("Generate practice questions for physics") == "generate_questions"
        assert orch.classify_intent("More questions like this please") == "generate_questions"

    def test_plan_intent(self, app):
        orch = self._make_orchestrator(app)
        assert orch.classify_intent("Create a study plan for me") == "get_plan"
        assert orch.classify_intent("What should I study today?") == "get_plan"
        assert orch.classify_intent("I'm stressed about exams") == "get_plan"
        assert orch.classify_intent("Give me a daily briefing") == "get_plan"


# ══════════════════════════════════════════════════════════════════════
# ─── Routing Tests ───────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════

class TestNewRouting:
    def test_vision_routes_correctly(self, app):
        with app.app_context():
            from orchestrator import Orchestrator
            from agents.base import AgentResponse

            orch = Orchestrator(user_id=1)
            mock_agent = MagicMock()
            mock_agent.analyze_handwriting.return_value = AgentResponse(
                content="Line 1: correct", agent="vision_agent", confidence=0.8,
            )
            orch._agents["vision"] = mock_agent

            result = orch.route(
                "analyze_handwriting", "Check my work",
                context={"image_data": b"fake", "question": "Solve x+2=5", "marks": 3},
            )
            assert result.agent == "vision_agent"
            mock_agent.analyze_handwriting.assert_called_once()

    def test_vision_without_image(self, app):
        with app.app_context():
            from orchestrator import Orchestrator

            orch = Orchestrator(user_id=1)
            result = orch.route(
                "analyze_handwriting", "Check my work",
                context={},
            )
            assert "upload" in result.content.lower() or "photo" in result.content.lower()

    def test_oral_routes_to_start(self, app):
        with app.app_context():
            from orchestrator import Orchestrator
            from agents.base import AgentResponse

            orch = Orchestrator(user_id=1)
            mock_agent = MagicMock()
            mock_agent.start_session.return_value = AgentResponse(
                content="Begin your oral...", agent="oral_exam_agent", confidence=0.9,
                metadata={"phase": "prepared"},
            )
            orch._agents["oral"] = mock_agent

            result = orch.route(
                "practice_oral", "Practice my oral",
                context={"subject": "English A", "text_title": "Hamlet"},
            )
            assert result.agent == "oral_exam_agent"
            mock_agent.start_session.assert_called_once()

    def test_oral_routes_to_respond(self, app):
        with app.app_context():
            from orchestrator import Orchestrator
            from agents.base import AgentResponse

            orch = Orchestrator(user_id=1)
            mock_agent = MagicMock()
            mock_agent.listen_and_respond.return_value = AgentResponse(
                content="Good point...", agent="oral_exam_agent", confidence=0.85,
                metadata={"phase": "follow_up"},
            )
            orch._agents["oral"] = mock_agent

            result = orch.route(
                "practice_oral", "The author uses symbolism...",
                context={"session_state": {"phase": "prepared"}, "session_id": 1},
            )
            mock_agent.listen_and_respond.assert_called_once()

    def test_feasibility_routes_correctly(self, app):
        with app.app_context():
            from orchestrator import Orchestrator
            from agents.base import AgentResponse

            orch = Orchestrator(user_id=1)
            mock_agent = MagicMock()
            mock_agent.check_feasibility.return_value = AgentResponse(
                content="Score: 8/10", agent="coursework_ide_agent", confidence=0.85,
            )
            orch._agents["coursework_ide"] = mock_agent

            result = orch.route(
                "check_feasibility", "Is this good?",
                context={"text": "Effect of pH on enzyme activity", "subject": "Biology"},
            )
            assert result.agent == "coursework_ide_agent"

    def test_data_analysis_routes_correctly(self, app):
        with app.app_context():
            from orchestrator import Orchestrator
            from agents.base import AgentResponse

            orch = Orchestrator(user_id=1)
            mock_agent = MagicMock()
            mock_agent.analyze_data.return_value = AgentResponse(
                content="Mean: 5.2", agent="coursework_ide_agent", confidence=0.8,
            )
            orch._agents["coursework_ide"] = mock_agent

            result = orch.route(
                "analyze_data", "Analyze this data",
                context={"data": "1,2,3,4,5", "subject": "Biology"},
            )
            assert result.agent == "coursework_ide_agent"

    def test_tok_routes_correctly(self, app):
        with app.app_context():
            from orchestrator import Orchestrator
            from agents.base import AgentResponse

            orch = Orchestrator(user_id=1)
            mock_agent = MagicMock()
            mock_agent.synthesize.return_value = AgentResponse(
                content="Biology and History connect through...",
                agent="tok_synthesis_agent", confidence=0.85,
            )
            orch._agents["tok"] = mock_agent

            result = orch.route(
                "tok_synthesis", "How do Biology and History connect for TOK?",
                context={"subject": "Biology"},
            )
            assert result.agent == "tok_synthesis_agent"

    def test_question_gen_routes_correctly(self, app):
        with app.app_context():
            from orchestrator import Orchestrator
            from agents.base import AgentResponse

            orch = Orchestrator(user_id=1)
            mock_agent = MagicMock()
            mock_agent.generate_parametric.return_value = AgentResponse(
                content="Question 1: ...", agent="question_gen_agent", confidence=0.85,
                metadata={"total_generated": 3, "total_verified": 2},
            )
            orch._agents["question_gen"] = mock_agent

            result = orch.route(
                "generate_questions", "Give me physics questions",
                context={"subject": "Physics", "topic": "Mechanics"},
            )
            assert result.agent == "question_gen_agent"

    def test_executive_routes_to_briefing(self, app):
        with app.app_context():
            from orchestrator import Orchestrator
            from agents.base import AgentResponse

            orch = Orchestrator(user_id=1)
            mock_agent = MagicMock()
            mock_agent.daily_briefing.return_value = AgentResponse(
                content="Good morning!", agent="executive_agent", confidence=0.85,
            )
            orch._agents["executive"] = mock_agent

            result = orch.route("get_plan", "What should I focus on?")
            assert result.agent == "executive_agent"
            mock_agent.daily_briefing.assert_called_once()

    def test_executive_routes_to_plan(self, app):
        with app.app_context():
            from orchestrator import Orchestrator
            from agents.base import AgentResponse

            orch = Orchestrator(user_id=1)
            mock_agent = MagicMock()
            mock_agent.generate_smart_plan.return_value = AgentResponse(
                content="Day 1: Biology...", agent="executive_agent", confidence=0.85,
            )
            orch._agents["executive"] = mock_agent

            result = orch.route("get_plan", "Create a study plan for next week")
            mock_agent.generate_smart_plan.assert_called_once()

    def test_executive_routes_to_reprioritize(self, app):
        with app.app_context():
            from orchestrator import Orchestrator
            from agents.base import AgentResponse

            orch = Orchestrator(user_id=1)
            mock_agent = MagicMock()
            mock_agent.reprioritize.return_value = AgentResponse(
                content="Updated plan...", agent="executive_agent", confidence=0.8,
            )
            orch._agents["executive"] = mock_agent

            result = orch.route("get_plan", "My chemistry deadline moved to next week")
            mock_agent.reprioritize.assert_called_once()


# ══════════════════════════════════════════════════════════════════════
# ─── Agent Unit Tests ────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════

class TestVisionAgent:
    def test_init_without_keys(self, app):
        with app.app_context():
            from agents.vision_agent import VisionAgent
            agent = VisionAgent()
            agent._provider = "none"
            result = agent.analyze_handwriting(b"fake", "Solve x=5", "Math")
            assert result.confidence == 0.0

    def test_ecf_response_parsing(self, app):
        with app.app_context():
            from agents.vision_agent import VisionAgent
            agent = VisionAgent()

            raw = (
                "ERROR_LINE: 3\n"
                "LINE_ANALYSIS:\n"
                "Line 1: M - Correct setup\n"
                "Line 2: A - Correct calculation\n"
                "Line 3: 0 - Wrong substitution\n"
                "Line 4: ECF - Used wrong value correctly\n"
                "TOTAL_EARNED: 3 / 5\n"
                "ECF_MARKS: 1\n"
                "SUMMARY: First error at line 3\n"
                "ADVICE: Check your substitution step"
            )
            result = agent._parse_ecf_response(raw, 5)
            assert result["error_line"] == 3
            assert result["earned_marks"] == 3
            assert result["ecf_marks"] == 1
            assert len(result["line_analysis"]) == 4

    def test_format_response(self, app):
        with app.app_context():
            from agents.vision_agent import VisionAgent
            agent = VisionAgent()

            steps = [{"line_num": 1, "expression": "F=ma", "description": "Newton's law"}]
            ecf = {"earned_marks": 3, "ecf_marks": 1, "error_line": 2, "line_analysis": ["Line 1: A - Correct"]}
            content = agent._format_response(steps, ecf, 5, "Physics")
            assert "Physics" in content
            assert "3/5" in content
            assert "1 ECF mark" in content


class TestOralExamAgent:
    def test_init_without_keys(self, app):
        with app.app_context():
            from agents.oral_exam_agent import OralExamAgent
            agent = OralExamAgent()
            agent._provider = "none"
            result = agent.start_session("English A", "Hamlet")
            assert result.confidence == 0.0

    def test_rubric_type_detection(self, app):
        with app.app_context():
            from agents.oral_exam_agent import OralExamAgent
            agent = OralExamAgent()
            assert agent._get_rubric_type("English A") == "language_a"
            assert agent._get_rubric_type("French B") == "language_b"
            assert agent._get_rubric_type("Spanish B") == "language_b"

    def test_grading_parser(self, app):
        with app.app_context():
            from agents.oral_exam_agent import OralExamAgent, ORAL_RUBRICS
            agent = OralExamAgent()

            raw = (
                "CRITERION: Knowledge and understanding\n"
                "SCORE: 7 / 10\n"
                "JUSTIFICATION: Good textual references\n"
                "IMPROVEMENT: Add more specific quotes\n"
                "CRITERION: Analysis and evaluation\n"
                "SCORE: 6 / 10\n"
                "JUSTIFICATION: Decent analysis\n"
                "IMPROVEMENT: Deeper critical thinking\n"
            )
            scores = agent._parse_grading(raw, ORAL_RUBRICS["language_a"])
            assert "Knowledge and understanding" in scores
            assert scores["Knowledge and understanding"]["earned"] == 7


class TestCourseworkIDEAgent:
    def test_init_without_keys(self, app):
        with app.app_context():
            from agents.coursework_ide_agent import CourseworkIDEAgent
            agent = CourseworkIDEAgent()
            agent._provider = "none"
            result = agent.check_feasibility("topic", "Biology")
            assert result.confidence == 0.0

    def test_feasibility_parser(self, app):
        with app.app_context():
            from agents.coursework_ide_agent import CourseworkIDEAgent
            agent = CourseworkIDEAgent()
            raw = "FEASIBILITY_SCORE: 8\nVERDICT: Good\nOther text"
            result = agent._parse_feasibility(raw)
            assert result["score"] == 8
            assert result["verdict"] == "Good"


class TestTOKSynthesisAgent:
    def test_init_without_keys(self, app):
        with app.app_context():
            from agents.tok_synthesis_agent import TOKSynthesisAgent
            agent = TOKSynthesisAgent()
            agent._provider = "none"
            result = agent.synthesize("Connect Biology and History")
            assert result.confidence == 0.0

    def test_aok_mapping(self, app):
        with app.app_context():
            from agents.tok_synthesis_agent import TOKSynthesisAgent
            agent = TOKSynthesisAgent()

            bio = agent.map_aok("Biology")
            assert bio["aok"] == "Natural Sciences"
            assert "Reason" in bio["primary_wok"]

            hist = agent.map_aok("History")
            assert hist["aok"] == "History"

            math = agent.map_aok("Mathematics: AA")
            assert math["aok"] == "Mathematics"

    def test_aok_mapping_unknown(self, app):
        with app.app_context():
            from agents.tok_synthesis_agent import TOKSynthesisAgent
            agent = TOKSynthesisAgent()
            result = agent.map_aok("Unknown Subject XYZ")
            assert result["aok"] == "General"


class TestQuestionGenAgent:
    def test_init_without_keys(self, app):
        with app.app_context():
            from agents.question_gen_agent import QuestionGenAgent
            agent = QuestionGenAgent()
            agent._provider = "none"
            result = agent.generate_parametric("Mathematics", "Calculus")
            assert result.confidence == 0.0

    def test_question_parser(self, app):
        with app.app_context():
            from agents.question_gen_agent import QuestionGenAgent
            agent = QuestionGenAgent()

            raw = (
                "QUESTION_1:\n"
                "Question: Calculate the area under y=x^2 from 0 to 3\n"
                "Command_term: Calculate\n"
                "Marks: 4\n"
                "Model_answer: 9 square units\n"
                "Python_verification: import math; print(3**3/3)\n"
                "\n"
                "QUESTION_2:\n"
                "Question: Find the derivative of 3x^2+2x\n"
                "Command_term: Find\n"
                "Marks: 3\n"
                "Model_answer: 6x+2\n"
                "Python_verification: print('6x+2')\n"
            )
            questions = agent._parse_questions(raw)
            assert len(questions) == 2
            assert questions[0]["question"] == "Calculate the area under y=x^2 from 0 to 3"
            assert questions[0]["marks"] == 4
            assert questions[1]["command_term"] == "Find"

    def test_format_questions(self, app):
        with app.app_context():
            from agents.question_gen_agent import QuestionGenAgent
            agent = QuestionGenAgent()

            questions = [
                {"question": "Q1", "verified": True, "marks": 4, "command_term": "Calculate",
                 "model_answer": "42"},
                {"question": "Q2", "verified": False, "marks": 3, "command_term": "Find",
                 "model_answer": "7"},
            ]
            content = agent._format_questions(questions, "Mathematics", "Calculus")
            assert "Verified" in content
            assert "Unverified" in content
            assert "1/2" in content


class TestExecutiveAgent:
    def test_init_without_keys(self, app):
        with app.app_context():
            from agents.executive_agent import ExecutiveAgent
            agent = ExecutiveAgent()
            agent._provider = "none"
            result = agent.daily_briefing(1)
            assert result.confidence == 0.0

    def test_burnout_detection_no_activity(self, app):
        with app.app_context():
            from agents.executive_agent import ExecutiveAgent
            agent = ExecutiveAgent()
            result = agent.detect_burnout(1)
            assert result["risk_level"] == "low"
            assert isinstance(result["signals"], list)

    def test_burnout_detection_structure(self, app):
        with app.app_context():
            from agents.executive_agent import ExecutiveAgent
            agent = ExecutiveAgent()
            result = agent.detect_burnout(1)
            assert "risk_level" in result
            assert "signals" in result
            assert "recommendation" in result
            assert result["risk_level"] in ("low", "medium", "high")


# ══════════════════════════════════════════════════════════════════════
# ─── Memory Type Tests ───────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════

class TestMemoryTypeExtension:
    def test_area_of_knowledge_type_exists(self):
        from memory import MEMORY_TYPES
        assert "area_of_knowledge" in MEMORY_TYPES

    def test_remember_aok(self, app):
        with app.app_context():
            from memory import StudentMemory
            mem = StudentMemory(1)
            mem.remember(
                "area_of_knowledge",
                "aok_biology",
                "Biology maps to Natural Sciences",
                source="tok_synthesis",
            )
            memories = mem.recall("area_of_knowledge")
            assert len(memories) >= 1
            assert memories[0]["value"] == "Biology maps to Natural Sciences"

    def test_aok_in_prompt(self, app):
        with app.app_context():
            from memory import StudentMemory
            mem = StudentMemory(1)
            mem.remember("area_of_knowledge", "aok_test", "Test AoK value")
            prompt = mem.recall_for_prompt()
            assert "Areas of Knowledge" in prompt


# ══════════════════════════════════════════════════════════════════════
# ─── Seed AoK Mappings Tests ────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════

class TestAoKMappings:
    def test_all_subjects_have_required_keys(self):
        from seed_aok_mappings import AOK_MAPPINGS
        for subject, mapping in AOK_MAPPINGS.items():
            assert "aok" in mapping, f"{subject} missing 'aok'"
            assert "primary_wok" in mapping, f"{subject} missing 'primary_wok'"
            assert "secondary_wok" in mapping, f"{subject} missing 'secondary_wok'"
            assert isinstance(mapping["primary_wok"], list)
            assert len(mapping["primary_wok"]) >= 1

    def test_core_subjects_present(self):
        from seed_aok_mappings import AOK_MAPPINGS
        required = ["Biology", "Chemistry", "Physics", "Mathematics: AA",
                     "History", "Economics", "English A"]
        for subj in required:
            assert subj in AOK_MAPPINGS, f"Missing subject: {subj}"


# ══════════════════════════════════════════════════════════════════════
# ─── Endpoint Tests ──────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════

class TestEndpoints:
    def test_oral_start_requires_auth(self, client):
        resp = client.post("/api/oral/start", json={"subject": "English A"})
        assert resp.status_code in (302, 401)

    def test_oral_respond_requires_auth(self, client):
        resp = client.post("/api/oral/respond", json={"transcript": "test"})
        assert resp.status_code in (302, 401)

    def test_oral_grade_requires_auth(self, client):
        resp = client.post("/api/oral/grade", json={"session_state": {}})
        assert resp.status_code in (302, 401)

    def test_oral_history_requires_auth(self, client):
        resp = client.get("/api/oral/history")
        assert resp.status_code in (302, 401)

    def test_coursework_feasibility_requires_auth(self, client):
        resp = client.post("/api/coursework/check-feasibility", json={})
        assert resp.status_code in (302, 401)

    def test_coursework_analyze_data_requires_auth(self, client):
        resp = client.post("/api/coursework/analyze-data", json={})
        assert resp.status_code in (302, 401)

    def test_coursework_review_draft_requires_auth(self, client):
        resp = client.post("/api/coursework/review-draft", json={})
        assert resp.status_code in (302, 401)

    def test_parametric_questions_requires_auth(self, client):
        resp = client.post("/api/questions/generate-parametric", json={})
        assert resp.status_code in (302, 401)

    def test_daily_briefing_requires_auth(self, client):
        resp = client.get("/api/executive/daily-briefing")
        assert resp.status_code in (302, 401)

    def test_generate_plan_requires_auth(self, client):
        resp = client.post("/api/executive/generate-plan", json={})
        assert resp.status_code in (302, 401)

    def test_reprioritize_requires_auth(self, client):
        resp = client.post("/api/executive/reprioritize", json={})
        assert resp.status_code in (302, 401)

    def test_burnout_check_requires_auth(self, client):
        resp = client.get("/api/executive/burnout-check")
        assert resp.status_code in (302, 401)

    def test_oral_respond_requires_transcript(self, auth_client):
        resp = auth_client.post("/api/oral/respond",
                                json={"session_state": {}},
                                content_type="application/json")
        assert resp.status_code == 400

    def test_reprioritize_requires_event(self, auth_client):
        resp = auth_client.post("/api/executive/reprioritize",
                                json={},
                                content_type="application/json")
        assert resp.status_code == 400

    def test_oral_history_empty(self, auth_client):
        resp = auth_client.get("/api/oral/history")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_burnout_check_returns_structure(self, auth_client):
        resp = auth_client.get("/api/executive/burnout-check")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "risk_level" in data
        assert data["risk_level"] in ("low", "medium", "high")


# ══════════════════════════════════════════════════════════════════════
# ─── Graceful Fallback Tests for New Agents ──────────────────────────
# ══════════════════════════════════════════════════════════════════════

class TestNewAgentFallbacks:
    def test_vision_without_keys(self, app):
        with app.app_context():
            from agents.vision_agent import VisionAgent
            agent = VisionAgent()
            agent._provider = "none"
            agent._gemini_vision = None
            agent._gemini_model = None
            result = agent.analyze_handwriting(b"test", "Q", "Math")
            assert result.confidence == 0.0
            assert "API key" in result.content or "key" in result.content.lower()

    def test_oral_without_keys(self, app):
        with app.app_context():
            from agents.oral_exam_agent import OralExamAgent
            agent = OralExamAgent()
            agent._provider = "none"
            result = agent.start_session("English", "Text")
            assert result.confidence == 0.0

    def test_coursework_ide_without_keys(self, app):
        with app.app_context():
            from agents.coursework_ide_agent import CourseworkIDEAgent
            agent = CourseworkIDEAgent()
            agent._provider = "none"
            result = agent.check_feasibility("topic", "Biology")
            assert result.confidence == 0.0
            result2 = agent.analyze_data("1,2,3", "Biology")
            assert result2.confidence == 0.0
            result3 = agent.review_draft("draft text", "ia", "Biology")
            assert result3.confidence == 0.0

    def test_tok_without_keys(self, app):
        with app.app_context():
            from agents.tok_synthesis_agent import TOKSynthesisAgent
            agent = TOKSynthesisAgent()
            agent._provider = "none"
            result = agent.synthesize("Connect subjects")
            assert result.confidence == 0.0
            result2 = agent.suggest_connections("Bio", "Cells", "History", "WW2")
            assert result2.confidence == 0.0

    def test_question_gen_without_keys(self, app):
        with app.app_context():
            from agents.question_gen_agent import QuestionGenAgent
            agent = QuestionGenAgent()
            agent._provider = "none"
            result = agent.generate_parametric("Mathematics")
            assert result.confidence == 0.0

    def test_executive_without_keys(self, app):
        with app.app_context():
            from agents.executive_agent import ExecutiveAgent
            agent = ExecutiveAgent()
            agent._provider = "none"
            result = agent.daily_briefing(1)
            assert result.confidence == 0.0
            result2 = agent.generate_smart_plan(1)
            assert result2.confidence == 0.0
            result3 = agent.reprioritize(1, "deadline changed")
            assert result3.confidence == 0.0


# ══════════════════════════════════════════════════════════════════════
# ─── Intent Label Completeness ───────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════

class TestIntentLabels:
    def test_all_15_intents(self):
        from orchestrator import INTENT_LABELS
        assert len(INTENT_LABELS) == 15
        expected = {
            "grade_answer", "explain_concept", "help_question",
            "review_coursework", "find_research", "solve_stem",
            "general_chat", "analyze_handwriting", "practice_oral",
            "check_feasibility", "analyze_data", "tok_synthesis",
            "generate_questions", "get_plan", "admissions",
        }
        assert set(INTENT_LABELS) == expected
