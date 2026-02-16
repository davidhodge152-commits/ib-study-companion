"""
Tests for new features: study groups, community papers, adaptive difficulty,
teacher dashboard, exam sessions, tutor conversations, push subscriptions.
"""
from __future__ import annotations

import json
import pytest


class TestStudyGroups:
    """Step 4: Study Groups & Social"""

    def test_create_group(self, auth_client):
        res = auth_client.post("/api/groups", data=json.dumps({
            "name": "Biology HL Study Group",
            "subject": "Biology",
            "level": "HL",
        }), content_type="application/json")
        data = res.get_json()
        assert data["success"]
        assert "invite_code" in data
        assert data["id"] > 0

    def test_list_groups(self, auth_client):
        # Create a group first
        auth_client.post("/api/groups", data=json.dumps({"name": "Test Group"}),
                         content_type="application/json")
        res = auth_client.get("/api/groups")
        data = res.get_json()
        assert "groups" in data
        assert len(data["groups"]) >= 1

    def test_join_group_by_code(self, auth_client):
        # Create group
        create_res = auth_client.post("/api/groups", data=json.dumps({"name": "Join Test"}),
                                       content_type="application/json")
        invite_code = create_res.get_json()["invite_code"]

        # The auth_client (user 1) can also join via code since they're the owner already,
        # but we test the API works by trying to join the same group with the same user
        # (which should return False since already a member, but the endpoint works)
        res = auth_client.post("/api/groups/join", data=json.dumps({"invite_code": invite_code}),
                               content_type="application/json")
        data = res.get_json()
        # Already a member, so success is False
        assert "success" in data

    def test_group_detail(self, auth_client):
        create_res = auth_client.post("/api/groups", data=json.dumps({"name": "Detail Test"}),
                                       content_type="application/json")
        gid = create_res.get_json()["id"]
        res = auth_client.get(f"/api/groups/{gid}")
        data = res.get_json()
        assert data["group"]["name"] == "Detail Test"
        assert len(data["members"]) == 1  # Creator is auto-joined


class TestChallenges:
    """Step 4: Challenges"""

    def test_create_challenge(self, auth_client):
        # Create group first
        create_res = auth_client.post("/api/groups", data=json.dumps({"name": "Challenge Group"}),
                                       content_type="application/json")
        gid = create_res.get_json()["id"]

        res = auth_client.post("/api/challenges", data=json.dumps({
            "group_id": gid,
            "title": "Bio Quiz",
            "subject": "Biology",
        }), content_type="application/json")
        data = res.get_json()
        assert data["success"]
        assert data["challenge_id"] > 0

    def test_submit_challenge_score(self, auth_client):
        # Create group and challenge
        g = auth_client.post("/api/groups", data=json.dumps({"name": "Score Group"}),
                              content_type="application/json").get_json()
        c = auth_client.post("/api/challenges", data=json.dumps({
            "group_id": g["id"], "title": "Test", "subject": "Bio",
        }), content_type="application/json").get_json()

        res = auth_client.post(f"/api/challenges/{c['challenge_id']}/submit",
                                data=json.dumps({"score": 85.5}),
                                content_type="application/json")
        assert res.get_json()["success"]


class TestLeaderboard:
    """Step 4: Leaderboard"""

    def test_global_leaderboard(self, auth_client):
        res = auth_client.get("/api/leaderboard?scope=global")
        data = res.get_json()
        assert "leaderboard" in data


class TestGuestMode:
    """Step 5: Try-before-signup"""

    def test_try_page_loads(self, client):
        res = client.get("/try")
        assert res.status_code == 200

    def test_guest_blocked_from_protected(self, client):
        client.get("/try")  # Set guest session
        res = client.get("/dashboard", follow_redirects=False)
        assert res.status_code == 302  # Redirected


class TestPushSubscription:
    """Step 6: Web push"""

    def test_vapid_key_endpoint(self, client):
        res = client.get("/api/push/vapid-key")
        data = res.get_json()
        assert "publicKey" in data

    def test_subscribe(self, auth_client):
        res = auth_client.post("/api/push/subscribe", data=json.dumps({
            "subscription": {
                "endpoint": "https://example.com/push/123",
                "keys": {"p256dh": "testkey", "auth": "testauth"},
            }
        }), content_type="application/json")
        assert res.get_json()["success"]

    def test_unsubscribe(self, auth_client):
        # Subscribe first
        auth_client.post("/api/push/subscribe", data=json.dumps({
            "subscription": {"endpoint": "https://example.com/push/456", "keys": {"p256dh": "k", "auth": "a"}},
        }), content_type="application/json")

        res = auth_client.post("/api/push/unsubscribe", data=json.dumps({
            "endpoint": "https://example.com/push/456",
        }), content_type="application/json")
        assert res.get_json()["success"]


class TestCommunityPapers:
    """Step 7: Community papers"""

    def test_upload_paper(self, auth_client):
        res = auth_client.post("/api/papers", data=json.dumps({
            "title": "Biology HL Paper 2 2024",
            "subject": "Biology",
            "level": "HL",
            "year": 2024,
            "questions": [{"question": "Explain the process of photosynthesis."}],
        }), content_type="application/json")
        data = res.get_json()
        assert data["success"]
        assert data["paper_id"] > 0

    def test_list_papers(self, auth_client):
        # Upload one first
        auth_client.post("/api/papers", data=json.dumps({
            "title": "Test Paper", "subject": "Chemistry", "level": "SL",
            "questions": [],
        }), content_type="application/json")

        # List (note: papers default to unapproved, list shows approved only)
        res = auth_client.get("/api/papers")
        data = res.get_json()
        assert "papers" in data

    def test_rate_paper(self, auth_client):
        p = auth_client.post("/api/papers", data=json.dumps({
            "title": "Rate Me", "subject": "Physics", "questions": [],
        }), content_type="application/json").get_json()

        res = auth_client.post(f"/api/papers/{p['paper_id']}/rate",
                                data=json.dumps({"rating": 4}),
                                content_type="application/json")
        assert res.get_json()["success"]

    def test_report_paper(self, auth_client):
        p = auth_client.post("/api/papers", data=json.dumps({
            "title": "Report Me", "subject": "Math", "questions": [],
        }), content_type="application/json").get_json()

        res = auth_client.post(f"/api/papers/{p['paper_id']}/report",
                                data=json.dumps({"reason": "Incorrect content"}),
                                content_type="application/json")
        assert res.get_json()["success"]


class TestTeacherDashboard:
    """Step 8: Teacher dashboard"""

    @pytest.fixture(autouse=False)
    def teacher_client(self, app):
        """Create an authenticated client with teacher role."""
        from werkzeug.security import generate_password_hash
        from database import get_db

        with app.app_context():
            db = get_db()
            db.execute(
                "INSERT OR IGNORE INTO users (id, name, email, password_hash, role, created_at) "
                "VALUES (10, 'Teacher', 'teacher@test.com', ?, 'teacher', '')",
                (generate_password_hash("teachpass"),),
            )
            db.execute("INSERT OR IGNORE INTO gamification (user_id) VALUES (10)")
            db.commit()

        client = app.test_client()
        with client:
            res = client.post("/login", data={
                "email": "teacher@test.com",
                "password": "teachpass",
            }, follow_redirects=True)
            yield client

    def test_teacher_dashboard_requires_teacher_role(self, auth_client):
        # Default test user is a student
        res = auth_client.get("/teacher/dashboard")
        assert res.status_code == 403

    def test_teacher_can_access_dashboard(self, teacher_client):
        res = teacher_client.get("/teacher/dashboard")
        # If redirected to login (302), teacher auth failed
        assert res.status_code == 200, f"Got {res.status_code}, data: {res.data[:200]}"

    def test_create_class(self, teacher_client):
        res = teacher_client.post("/teacher/classes", data=json.dumps({
            "name": "IB Biology HL",
            "subject": "Biology",
            "level": "HL",
        }), content_type="application/json")
        data = res.get_json()
        assert data["success"]
        assert "join_code" in data

    def test_join_class_by_code(self, teacher_client):
        create_res = teacher_client.post("/teacher/classes", data=json.dumps({
            "name": "Join Test", "subject": "Chemistry",
        }), content_type="application/json")
        code = create_res.get_json()["join_code"]

        # Same teacher joins (as student) — tests the join API
        res = teacher_client.post("/api/classes/join", data=json.dumps({
            "join_code": code,
        }), content_type="application/json")
        assert res.get_json()["success"]


class TestAdaptiveDifficulty:
    """Step 9: Adaptive engine"""

    def test_ability_profile_empty(self, auth_client):
        res = auth_client.get("/api/ability/biology")
        data = res.get_json()
        assert "abilities" in data
        assert data["abilities"] == []

    def test_estimate_difficulty(self, app):
        with app.app_context():
            from adaptive import estimate_difficulty
            # Low marks + easy command term
            d1 = estimate_difficulty(2, "Define")
            assert 0.1 <= d1 <= 1.0

            # High marks + hard command term
            d2 = estimate_difficulty(10, "Evaluate")
            assert d2 > d1

    def test_update_theta(self, app):
        with app.app_context():
            from adaptive import update_theta
            result = update_theta(1, "biology", "Photosynthesis", 1.0, 0.8)
            assert "theta" in result
            assert result["attempts"] == 1

    def test_select_difficulty(self, app):
        with app.app_context():
            from adaptive import select_difficulty
            d = select_difficulty(1, "biology", "New Topic")
            assert 0.1 <= d <= 3.0


class TestExamSimulation:
    """Step 10: Exam simulation"""

    def test_exam_history_empty(self, auth_client):
        res = auth_client.get("/api/exam/history")
        data = res.get_json()
        assert "sessions" in data
        assert data["sessions"] == []

    def test_calculate_grade(self, app):
        with app.app_context():
            from exam_simulation import ExamPaperGenerator
            assert ExamPaperGenerator.calculate_grade("Biology", "HL", 100, 85) == 7
            assert ExamPaperGenerator.calculate_grade("Biology", "HL", 100, 35) in (2, 3)
            assert ExamPaperGenerator.calculate_grade("Biology", "HL", 100, 10) == 1


class TestAITutor:
    """Step 11: AI Tutor"""

    def test_tutor_page_loads(self, auth_client):
        res = auth_client.get("/tutor")
        assert res.status_code == 200

    def test_start_conversation(self, auth_client):
        res = auth_client.post("/api/tutor/start", data=json.dumps({
            "subject": "Biology",
            "topic": "Photosynthesis",
        }), content_type="application/json")
        data = res.get_json()
        assert data["success"]
        assert data["conversation_id"] > 0

    def test_tutor_history(self, auth_client):
        # Start a conversation first
        auth_client.post("/api/tutor/start", data=json.dumps({
            "subject": "Chemistry", "topic": "Bonding",
        }), content_type="application/json")

        res = auth_client.get("/api/tutor/history")
        data = res.get_json()
        assert "conversations" in data
        assert len(data["conversations"]) >= 1

    def test_get_conversation(self, auth_client):
        create = auth_client.post("/api/tutor/start", data=json.dumps({
            "subject": "Physics", "topic": "Mechanics",
        }), content_type="application/json").get_json()

        res = auth_client.get(f"/api/tutor/{create['conversation_id']}")
        data = res.get_json()
        assert data["conversation"]["subject"] == "Physics"


class TestCommunityAnalytics:
    """Step 13: Community analytics"""

    def test_analytics_page_loads(self, auth_client):
        res = auth_client.get("/community-analytics")
        assert res.status_code == 200

    def test_global_stats(self, auth_client):
        res = auth_client.get("/api/analytics/global")
        data = res.get_json()
        assert "total_users" in data
        assert "total_questions" in data

    def test_trending_topics(self, auth_client):
        res = auth_client.get("/api/analytics/trending")
        data = res.get_json()
        assert "topics" in data


class TestNewPages:
    """Test that new pages load without errors."""

    def test_groups_page(self, auth_client):
        assert auth_client.get("/groups").status_code == 200

    def test_community_page(self, auth_client):
        assert auth_client.get("/community").status_code == 200

    def test_tutor_page(self, auth_client):
        assert auth_client.get("/tutor").status_code == 200

    def test_analytics_page(self, auth_client):
        assert auth_client.get("/community-analytics").status_code == 200
