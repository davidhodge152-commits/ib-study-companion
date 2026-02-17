"""Tests for HITL Monetization Infrastructure.

Covers all 7 systems:
1. Credit/Token Economy
2. Subscription Tiers & Feature Gating
3. SOS Detection & Micro-Tutoring Pipeline
4. Examiner Review Pipeline
5. Teacher Batch Grading
6. Enhanced Parent Portal
7. University Admissions Profile & Agent
"""

from __future__ import annotations

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch


# ═══════════════════════════════════════════════════════════════════
# System 1: Credit/Token Economy
# ═══════════════════════════════════════════════════════════════════


class TestCreditStoreDB:
    def test_initial_balance_is_zero(self, app):
        with app.app_context():
            from credit_store import CreditStoreDB
            store = CreditStoreDB(1)
            assert store.balance() == 0

    def test_credit_adds_balance(self, app):
        with app.app_context():
            from credit_store import CreditStoreDB
            store = CreditStoreDB(1)
            result = store.credit(500, "purchase", "Test purchase")
            assert result["success"] is True
            assert result["balance_after"] == 500
            assert store.balance() == 500

    def test_debit_reduces_balance(self, app):
        with app.app_context():
            from credit_store import CreditStoreDB
            store = CreditStoreDB(1)
            store.credit(500, "purchase", "Initial")
            result = store.debit(200, "oral_practice", "Test debit")
            assert result["success"] is True
            assert result["balance_after"] == 300
            assert store.balance() == 300

    def test_debit_fails_insufficient_credits(self, app):
        with app.app_context():
            from credit_store import CreditStoreDB
            store = CreditStoreDB(1)
            store.credit(100, "purchase", "Small amount")
            result = store.debit(500, "examiner_review", "Too expensive")
            assert result["success"] is False
            assert store.balance() == 100

    def test_has_credits(self, app):
        with app.app_context():
            from credit_store import CreditStoreDB
            store = CreditStoreDB(1)
            assert store.has_credits(1) is False
            store.credit(100, "purchase")
            assert store.has_credits(100) is True
            assert store.has_credits(101) is False

    def test_allocate_monthly(self, app):
        with app.app_context():
            from credit_store import CreditStoreDB
            store = CreditStoreDB(1)
            store.allocate_monthly(200)
            assert store.balance() == 200

    def test_transaction_history(self, app):
        with app.app_context():
            from credit_store import CreditStoreDB
            store = CreditStoreDB(1)
            store.credit(500, "purchase", "Buy credits")
            store.debit(50, "oral_practice", "Used feature")
            history = store.transaction_history()
            assert len(history) == 2
            assert history[0]["amount"] == -50  # Most recent first
            assert history[1]["amount"] == 500

    def test_lifetime_purchased_tracks(self, app):
        with app.app_context():
            from credit_store import CreditStoreDB
            from database import get_db
            store = CreditStoreDB(1)
            store.credit(100, "purchase")
            store.credit(200, "purchase")
            db = get_db()
            row = db.execute("SELECT lifetime_purchased FROM credit_balances WHERE user_id=1").fetchone()
            assert row["lifetime_purchased"] == 300

    def test_feature_costs_defined(self, app):
        from credit_store import FEATURE_COSTS
        assert "oral_practice" in FEATURE_COSTS
        assert "examiner_review" in FEATURE_COSTS
        assert FEATURE_COSTS["examiner_review"] == 500


class TestCreditsAPI:
    def test_balance_endpoint(self, auth_client):
        resp = auth_client.get("/api/credits/balance")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "balance" in data
        assert "transactions" in data

    def test_purchase_endpoint(self, auth_client):
        resp = auth_client.post("/api/credits/purchase",
                                json={"amount": 500})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["balance_after"] == 500

    def test_purchase_invalid_amount(self, auth_client):
        resp = auth_client.post("/api/credits/purchase",
                                json={"amount": 0})
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════
# System 2: Subscription Tiers & Feature Gating
# ═══════════════════════════════════════════════════════════════════


class TestSubscriptionStoreDB:
    def test_default_plan_is_free(self, app):
        with app.app_context():
            from subscription_store import SubscriptionStoreDB
            store = SubscriptionStoreDB(1)
            plan = store.current_plan()
            assert plan["plan_id"] == "free"

    def test_upgrade_plan(self, app):
        with app.app_context():
            from subscription_store import SubscriptionStoreDB
            store = SubscriptionStoreDB(1)
            store.upgrade("explorer")
            plan = store.current_plan()
            assert plan["plan_id"] == "explorer"

    def test_upgrade_allocates_credits(self, app):
        with app.app_context():
            from subscription_store import SubscriptionStoreDB
            from credit_store import CreditStoreDB
            store = SubscriptionStoreDB(1)
            store.upgrade("explorer")
            credits = CreditStoreDB(1)
            assert credits.balance() == 200

    def test_invalid_plan_raises(self, app):
        with app.app_context():
            from subscription_store import SubscriptionStoreDB
            store = SubscriptionStoreDB(1)
            with pytest.raises(ValueError):
                store.upgrade("nonexistent")

    def test_cancel_plan(self, app):
        with app.app_context():
            from subscription_store import SubscriptionStoreDB
            store = SubscriptionStoreDB(1)
            store.upgrade("explorer")
            store.cancel()
            plan = store.current_plan()
            assert plan["status"] == "cancelled"

    def test_is_feature_allowed_free(self, app):
        with app.app_context():
            from subscription_store import SubscriptionStoreDB
            store = SubscriptionStoreDB(1)
            assert store.is_feature_allowed("grading") is True
            assert store.is_feature_allowed("oral_practice") is False

    def test_is_feature_allowed_explorer(self, app):
        with app.app_context():
            from subscription_store import SubscriptionStoreDB
            store = SubscriptionStoreDB(1)
            store.upgrade("explorer")
            assert store.is_feature_allowed("oral_practice") is True
            assert store.is_feature_allowed("examiner_review") is False

    def test_plan_limits(self, app):
        with app.app_context():
            from subscription_store import SubscriptionStoreDB
            store = SubscriptionStoreDB(1)
            limits = store.plan_limits()
            assert limits["max_subjects"] == 3
            assert limits["plan_id"] == "free"


class TestSubscriptionAPI:
    def test_current_plan_endpoint(self, auth_client):
        resp = auth_client.get("/api/subscription/current")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "plan" in data
        assert "limits" in data

    def test_upgrade_endpoint(self, auth_client):
        resp = auth_client.post("/api/subscription/upgrade",
                                json={"plan_id": "explorer"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True


# ═══════════════════════════════════════════════════════════════════
# System 3: SOS Detection & Micro-Tutoring Pipeline
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def seeded_failing_grades(app):
    """Seed grade data with repeated low scores to trigger SOS."""
    with app.app_context():
        from database import get_db
        db = get_db()
        base_time = datetime.now() - timedelta(days=3)
        for i in range(4):
            ts = (base_time + timedelta(hours=i)).isoformat()
            db.execute(
                "INSERT INTO grades (user_id, subject, subject_display, level, "
                "command_term, grade, percentage, mark_earned, mark_total, "
                "strengths, improvements, examiner_tip, topic, timestamp) "
                "VALUES (1, 'biology', 'Biology', 'HL', 'Explain', 2, 25, 1, 4, "
                "'[]', '[\"Needs more detail\", \"Missing key terms\"]', "
                "'Study harder', 'Cell Biology', ?)",
                (ts,),
            )
        db.commit()


class TestSOSDetector:
    def test_no_sos_without_failures(self, app):
        with app.app_context():
            from sos_detector import SOSDetector
            detector = SOSDetector(1)
            alerts = detector.check_for_sos()
            assert alerts == []

    def test_sos_triggers_on_repeated_failures(self, app, seeded_failing_grades):
        with app.app_context():
            from sos_detector import SOSDetector
            detector = SOSDetector(1)
            alerts = detector.check_for_sos()
            assert len(alerts) >= 1
            alert = alerts[0]
            assert alert["subject"] == "biology"
            assert alert["topic"] == "Cell Biology"
            assert alert["failure_count"] >= 3
            assert alert["status"] == "active"

    def test_active_alerts(self, app, seeded_failing_grades):
        with app.app_context():
            from sos_detector import SOSDetector
            detector = SOSDetector(1)
            detector.check_for_sos()
            alerts = detector.active_alerts()
            assert len(alerts) >= 1

    def test_build_tutor_context(self, app, seeded_failing_grades):
        with app.app_context():
            from sos_detector import SOSDetector
            detector = SOSDetector(1)
            alerts = detector.check_for_sos()
            assert len(alerts) >= 1
            context = detector.build_tutor_context(alerts[0]["id"])
            assert context["subject"] == "biology"
            assert context["topic"] == "Cell Biology"
            assert "error_history" in context

    def test_request_session_requires_credits(self, app, seeded_failing_grades):
        with app.app_context():
            from sos_detector import SOSDetector
            detector = SOSDetector(1)
            alerts = detector.check_for_sos()
            result = detector.request_session(alerts[0]["id"])
            assert result["success"] is False
            assert "credits" in result["error"].lower()

    def test_request_session_with_credits(self, app, seeded_failing_grades):
        with app.app_context():
            from sos_detector import SOSDetector
            from credit_store import CreditStoreDB
            CreditStoreDB(1).credit(500, "purchase")
            detector = SOSDetector(1)
            alerts = detector.check_for_sos()
            result = detector.request_session(alerts[0]["id"])
            assert result["success"] is True
            assert "request_id" in result

    def test_complete_session(self, app, seeded_failing_grades):
        with app.app_context():
            from sos_detector import SOSDetector
            from credit_store import CreditStoreDB
            from database import get_db
            CreditStoreDB(1).credit(500, "purchase")
            detector = SOSDetector(1)
            alerts = detector.check_for_sos()
            result = detector.request_session(alerts[0]["id"])
            req_id = result["request_id"]

            # Create a teacher user
            db = get_db()
            db.execute(
                "INSERT INTO users (id, name, email, password_hash, role) "
                "VALUES (2, 'Test Teacher', 'teacher@example.com', 'hash', 'teacher')"
            )
            db.commit()

            SOSDetector.complete_session(req_id, 2)
            req = SOSDetector.get_tutor_request(req_id)
            assert req["status"] == "completed"


class TestSOSAPI:
    def test_sos_status_endpoint(self, auth_client):
        resp = auth_client.get("/api/sos/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "alerts" in data


# ═══════════════════════════════════════════════════════════════════
# System 4: Examiner Review Pipeline
# ═══════════════════════════════════════════════════════════════════


class TestExaminerPipeline:
    def test_generate_ai_diagnostic(self, app):
        with app.app_context():
            from examiner_pipeline import ExaminerPipeline
            pipeline = ExaminerPipeline()
            diagnostic = pipeline.generate_ai_diagnostic(
                "This is my IA about cell division...",
                "ia", "biology",
            )
            assert "word_count" in diagnostic
            assert diagnostic["word_count"] > 0
            assert "formatting_issues" in diagnostic

    def test_submit_for_review_requires_credits(self, app):
        with app.app_context():
            from examiner_pipeline import ExaminerPipeline
            pipeline = ExaminerPipeline()
            result = pipeline.submit_for_review(
                1, "ia", "biology", "Cell Division IA",
                "My IA content here...",
            )
            assert result["success"] is False
            assert "credits" in result["error"].lower()

    def test_submit_for_review_with_credits(self, app):
        with app.app_context():
            from examiner_pipeline import ExaminerPipeline
            from credit_store import CreditStoreDB
            CreditStoreDB(1).credit(1000, "purchase")
            pipeline = ExaminerPipeline()
            result = pipeline.submit_for_review(
                1, "ia", "biology", "Cell Division IA",
                "My IA content here about cell division and mitosis...",
            )
            assert result["success"] is True
            assert "review_id" in result
            assert "ai_diagnostic" in result

    def test_assign_to_examiner(self, app):
        with app.app_context():
            from examiner_pipeline import ExaminerPipeline
            from credit_store import CreditStoreDB
            from database import get_db
            CreditStoreDB(1).credit(1000, "purchase")

            # Create teacher
            db = get_db()
            db.execute(
                "INSERT OR IGNORE INTO users (id, name, email, password_hash, role) "
                "VALUES (2, 'Test Examiner', 'examiner@example.com', 'hash', 'teacher')"
            )
            db.commit()

            pipeline = ExaminerPipeline()
            result = pipeline.submit_for_review(
                1, "ia", "biology", "Test IA", "Content...",
            )
            review_id = result["review_id"]
            ExaminerPipeline.assign_to_examiner(review_id, 2)
            review = ExaminerPipeline.get_review(review_id)
            assert review["status"] == "assigned"
            assert review["examiner_id"] == 2

    def test_complete_review(self, app):
        with app.app_context():
            from examiner_pipeline import ExaminerPipeline
            from credit_store import CreditStoreDB
            from database import get_db
            CreditStoreDB(1).credit(1000, "purchase")

            db = get_db()
            db.execute(
                "INSERT OR IGNORE INTO users (id, name, email, password_hash, role) "
                "VALUES (2, 'Test Examiner', 'examiner@example.com', 'hash', 'teacher')"
            )
            db.commit()

            pipeline = ExaminerPipeline()
            result = pipeline.submit_for_review(
                1, "ee", "history", "WW2 Essay", "Extended essay about WW2...",
            )
            review_id = result["review_id"]
            ExaminerPipeline.assign_to_examiner(review_id, 2)
            ExaminerPipeline.submit_examiner_feedback(
                review_id, "Good analysis but needs more sources.", "B",
            )
            review = ExaminerPipeline.get_review(review_id)
            assert review["status"] == "reviewed"
            assert review["examiner_grade"] == "B"

    def test_deliver_to_student(self, app):
        with app.app_context():
            from examiner_pipeline import ExaminerPipeline
            from credit_store import CreditStoreDB
            CreditStoreDB(1).credit(1000, "purchase")

            pipeline = ExaminerPipeline()
            result = pipeline.submit_for_review(
                1, "tok_essay", "TOK", "Knowledge and Art", "TOK essay...",
            )
            ExaminerPipeline.submit_examiner_feedback(
                result["review_id"], "Interesting perspectives.", "A",
            )
            ExaminerPipeline.deliver_to_student(result["review_id"])
            review = ExaminerPipeline.get_review(result["review_id"])
            assert review["status"] == "delivered"

    def test_student_reviews(self, app):
        with app.app_context():
            from examiner_pipeline import ExaminerPipeline
            from credit_store import CreditStoreDB
            CreditStoreDB(1).credit(2000, "purchase")

            pipeline = ExaminerPipeline()
            pipeline.submit_for_review(1, "ia", "bio", "IA1", "Content1...")
            pipeline.submit_for_review(1, "ee", "hist", "EE1", "Content2...")
            reviews = ExaminerPipeline.student_reviews(1)
            assert len(reviews) == 2

    def test_pending_reviews(self, app):
        with app.app_context():
            from examiner_pipeline import ExaminerPipeline
            from credit_store import CreditStoreDB
            CreditStoreDB(1).credit(1000, "purchase")

            pipeline = ExaminerPipeline()
            pipeline.submit_for_review(1, "ia", "bio", "Test", "Content...")
            pending = ExaminerPipeline.pending_reviews()
            assert len(pending) >= 1

    def test_word_count_formatting_issue(self, app):
        with app.app_context():
            from examiner_pipeline import ExaminerPipeline
            pipeline = ExaminerPipeline()
            # Generate a text exceeding IA limit (2200 words)
            long_text = " ".join(["word"] * 3000)
            diagnostic = pipeline.generate_ai_diagnostic(long_text, "ia", "biology")
            assert any("word count" in issue.lower() for issue in diagnostic["formatting_issues"])


# ═══════════════════════════════════════════════════════════════════
# System 5: Teacher Batch Grading
# ═══════════════════════════════════════════════════════════════════


class TestBatchGradingAgent:
    def test_generate_class_summary_empty(self, app):
        with app.app_context():
            from agents.batch_grading_agent import BatchGradingAgent
            agent = BatchGradingAgent()
            summary = agent.generate_class_summary([])
            assert summary["avg_grade"] == 0
            assert summary["grade_distribution"] == {}

    def test_generate_class_summary(self, app):
        with app.app_context():
            from agents.batch_grading_agent import BatchGradingAgent
            agent = BatchGradingAgent()
            results = [
                {"student_name": "Alice", "grade": 6, "improvements": ["Needs examples"],
                 "criterion_scores": {"A": 4, "B": 3}, "ai_text_risk": "low"},
                {"student_name": "Bob", "grade": 4, "improvements": ["Needs examples", "Structure"],
                 "criterion_scores": {"A": 2, "B": 3}, "ai_text_risk": "high"},
                {"student_name": "Carol", "grade": 7, "improvements": [],
                 "criterion_scores": {"A": 5, "B": 4}, "ai_text_risk": "low"},
            ]
            summary = agent.generate_class_summary(results)
            assert summary["total_graded"] == 3
            assert summary["avg_grade"] > 0
            assert "Bob" in summary["ai_text_flags"]

    def test_detect_ai_text_low_risk(self, app):
        with app.app_context():
            from agents.batch_grading_agent import BatchGradingAgent
            agent = BatchGradingAgent()
            result = agent.detect_ai_text("This is a normal student essay about biology.")
            assert result["risk_level"] == "low"

    def test_detect_ai_text_high_risk(self, app):
        with app.app_context():
            from agents.batch_grading_agent import BatchGradingAgent
            agent = BatchGradingAgent()
            text = (
                "It is important to note that the process of photosynthesis is fundamental. "
                "Furthermore, it should be noted that chloroplasts play a key role. "
                "Moreover, the light-dependent reactions occur in the thylakoid membrane. "
                "Consequently, the Calvin cycle subsequently produces glucose. "
                "Notwithstanding the complexity, it is worth mentioning that ATP is generated. "
                "Henceforth, we can see that the aforementioned process is vital."
            )
            result = agent.detect_ai_text(text)
            assert result["risk_level"] in ("medium", "high")
            assert len(result["signals"]) > 0


# ═══════════════════════════════════════════════════════════════════
# System 6: Enhanced Parent Portal
# ═══════════════════════════════════════════════════════════════════


class TestParentAnalytics:
    def test_traffic_light_no_data(self, app):
        with app.app_context():
            from parent_analytics import ParentAnalytics
            analytics = ParentAnalytics(1)
            result = analytics.traffic_light()
            assert "subjects" in result
            # All subjects should show no_data without grades
            for s in result["subjects"]:
                assert s["status"] == "no_data"

    def test_traffic_light_with_grades(self, app, seeded_grades):
        with app.app_context():
            from parent_analytics import ParentAnalytics
            analytics = ParentAnalytics(1)
            result = analytics.traffic_light()
            subjects = result["subjects"]
            assert len(subjects) >= 1
            # At least one subject should have a valid status
            statuses = [s["status"] for s in subjects]
            valid = {"on_track", "watch", "action", "no_data"}
            assert all(s in valid for s in statuses)

    def test_sos_highlights_empty(self, app):
        with app.app_context():
            from parent_analytics import ParentAnalytics
            analytics = ParentAnalytics(1)
            highlights = analytics.sos_highlights()
            assert highlights == []

    def test_sos_highlights_with_alerts(self, app, seeded_failing_grades):
        with app.app_context():
            from sos_detector import SOSDetector
            SOSDetector(1).check_for_sos()
            from parent_analytics import ParentAnalytics
            analytics = ParentAnalytics(1)
            highlights = analytics.sos_highlights()
            assert len(highlights) >= 1
            assert "recommendation" in highlights[0]

    def test_weekly_digest(self, app):
        with app.app_context():
            from parent_analytics import ParentAnalytics
            analytics = ParentAnalytics(1)
            digest = analytics.weekly_digest()
            assert "questions_attempted" in digest
            assert "study_minutes" in digest
            assert "streak" in digest
            assert "avg_grade" in digest

    def test_action_items(self, app):
        with app.app_context():
            from parent_analytics import ParentAnalytics
            analytics = ParentAnalytics(1)
            items = analytics.action_items()
            assert len(items) >= 1
            assert len(items) <= 3


class TestParentPortalAPI:
    def test_traffic_light_invalid_token(self, client):
        resp = client.get("/api/parent/traffic-light/invalid-token")
        assert resp.status_code == 404

    def test_traffic_light_valid_token(self, app, auth_client):
        # Set up parent config before using auth_client
        with app.app_context():
            from db_stores import ParentConfigDB
            config = ParentConfigDB(1)
            config.save_all(enabled=True)
            config.generate_token()
            token = config.token

        resp = auth_client.get(f"/api/parent/traffic-light/{token}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "subjects" in data

    def test_digest_valid_token(self, app, auth_client):
        with app.app_context():
            from db_stores import ParentConfigDB
            config = ParentConfigDB(1)
            config.save_all(enabled=True)
            config.generate_token()
            token = config.token

        resp = auth_client.get(f"/api/parent/digest/{token}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "questions_attempted" in data


# ═══════════════════════════════════════════════════════════════════
# System 7: Admissions Profile & Agent
# ═══════════════════════════════════════════════════════════════════


class TestAdmissionsAgent:
    def test_gather_student_data(self, app):
        with app.app_context():
            from agents.admissions_agent import AdmissionsAgent
            agent = AdmissionsAgent()
            data = agent._gather_student_data(1)
            assert data["name"] == "Test Student"
            assert len(data["subjects"]) >= 1

    def test_generate_profile_no_provider(self, app):
        with app.app_context():
            from agents.admissions_agent import AdmissionsAgent
            agent = AdmissionsAgent()
            agent._provider = "none"
            result = agent.generate_profile(1)
            assert result.confidence == 0.0

    def test_draft_personal_statement_no_provider(self, app):
        with app.app_context():
            from agents.admissions_agent import AdmissionsAgent
            agent = AdmissionsAgent()
            agent._provider = "none"
            result = agent.draft_personal_statement(1)
            assert result.confidence == 0.0

    def test_suggest_universities_no_provider(self, app):
        with app.app_context():
            from agents.admissions_agent import AdmissionsAgent
            agent = AdmissionsAgent()
            agent._provider = "none"
            result = agent.suggest_universities(1)
            assert result.confidence == 0.0


class TestAdmissionsAPI:
    def test_profile_endpoint(self, auth_client):
        resp = auth_client.get("/api/admissions/profile")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════
# Orchestrator Integration
# ═══════════════════════════════════════════════════════════════════


class TestAdmissionsIntentClassification:
    def _make_orchestrator(self, app):
        with app.app_context():
            from orchestrator import Orchestrator
            return Orchestrator(user_id=1)

    def test_admissions_intent_from_keywords(self, app):
        orch = self._make_orchestrator(app)
        assert orch.classify_intent("Help me with my personal statement") == "admissions"
        assert orch.classify_intent("I need help with UCAS application") == "admissions"
        assert orch.classify_intent("Common App essay help") == "admissions"

    def test_admissions_in_intent_labels(self, app):
        from orchestrator import INTENT_LABELS
        assert "admissions" in INTENT_LABELS

    def test_admissions_routes_to_agent(self, app):
        with app.app_context():
            from orchestrator import Orchestrator
            orch = Orchestrator(user_id=1)

            mock_agent = MagicMock()
            from agents.base import AgentResponse
            mock_agent.generate_profile.return_value = AgentResponse(
                content="Profile generated", agent="admissions_agent",
                confidence=0.85, metadata={"profile": {}},
            )
            orch._agents["admissions"] = mock_agent

            result = orch.route("admissions", "Show me my admissions profile")
            assert result.agent == "admissions_agent"


# ═══════════════════════════════════════════════════════════════════
# Migration Tests
# ═══════════════════════════════════════════════════════════════════


class TestMigrations18to23:
    def test_credit_balances_table(self, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute("SELECT user_id, balance, lifetime_purchased, "
                       "monthly_allocation, last_allocation_date "
                       "FROM credit_balances LIMIT 1")

    def test_credit_transactions_table(self, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute("SELECT id, user_id, amount, type, feature, "
                       "description, balance_after, created_at "
                       "FROM credit_transactions LIMIT 1")

    def test_subscription_plans_seeded(self, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            plans = db.execute("SELECT id FROM subscription_plans").fetchall()
            plan_ids = {r["id"] for r in plans}
            assert plan_ids == {"free", "explorer", "scholar", "diploma_pass"}

    def test_user_subscriptions_table(self, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute("SELECT user_id, plan_id, status, started_at, "
                       "expires_at, cancelled_at "
                       "FROM user_subscriptions LIMIT 1")

    def test_sos_alerts_table(self, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute("SELECT id, user_id, subject, topic, command_term, "
                       "failure_count, avg_percentage, status, context_summary, "
                       "created_at, resolved_at FROM sos_alerts LIMIT 1")

    def test_tutoring_requests_table(self, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute("SELECT id, user_id, subject, topic, error_history, "
                       "context_summary, mastery_state, theta, status, tutor_id, "
                       "credits_charged, created_at, completed_at "
                       "FROM tutoring_requests LIMIT 1")

    def test_examiner_reviews_table(self, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute("SELECT id, user_id, doc_type, subject, title, "
                       "submission_text, ai_diagnostic, ai_predicted_grade, "
                       "status, examiner_id, examiner_feedback, examiner_grade, "
                       "examiner_video_url, credits_charged, submitted_at, "
                       "assigned_at, reviewed_at, delivered_at "
                       "FROM examiner_reviews LIMIT 1")

    def test_batch_grading_jobs_table(self, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute("SELECT id, teacher_id, class_id, assignment_title, "
                       "subject, doc_type, status, total_submissions, "
                       "processed_count, results, class_summary, "
                       "created_at, completed_at "
                       "FROM batch_grading_jobs LIMIT 1")

    def test_admissions_profiles_table(self, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            db.execute("SELECT id, user_id, predicted_total, subject_strengths, "
                       "extracurricular_summary, academic_interests, "
                       "writing_style_summary, recommended_universities, "
                       "personal_statement_draft, updated_at "
                       "FROM admissions_profiles LIMIT 1")
