"""Tests for db_stores.py — CRUD for all DB-backed store classes."""

import json
import pytest
from datetime import date, timedelta

from db_stores import (
    StudentProfileDB,
    GradeDetailLogDB,
    TopicProgressStoreDB,
    ActivityLogDB,
    ReviewScheduleDB,
    GamificationProfileDB,
    FlashcardDeckDB,
    MisconceptionLogDB,
    MockExamReportStoreDB,
    NotificationStoreDB,
    SharedQuestionStoreDB,
    StudyPlanDB,
    WritingProfileDB,
    ParentConfigDB,
    IBLifecycleDB,
    GradeHistoryDB,
    UploadStoreDB,
)
from profile import (
    SubjectEntry,
    GradeDetailEntry,
    Flashcard,
    Notification,
    MockExamReport,
    StudyTask,
    DailyPlan,
)
from lifecycle import CASReflection


class TestStudentProfileDB:
    def test_load_existing(self, app):
        with app.app_context():
            p = StudentProfileDB.load(1)
            assert p is not None
            assert p.name == "Test Student"
            assert len(p.subjects) == 3

    def test_exists(self, app):
        with app.app_context():
            assert StudentProfileDB.exists(1)
            assert not StudentProfileDB.exists(999)

    def test_create(self, app):
        with app.app_context():
            p = StudentProfileDB.create(
                name="New Student",
                subjects=[SubjectEntry("Physics", "HL", 6)],
                exam_session="Nov 2026",
                target_total_points=40,
                email="new@example.com",
            )
            assert p.name == "New Student"
            assert p.user_id > 1
            assert len(p.subjects) == 1

    def test_exam_countdown(self, app):
        with app.app_context():
            p = StudentProfileDB(1)
            cd = p.exam_countdown()
            assert "days" in cd
            assert "urgency" in cd
            assert cd["days"] >= 0

    def test_compute_gaps(self, app, seeded_grades):
        with app.app_context():
            p = StudentProfileDB(1)
            gl = GradeDetailLogDB(1)
            gaps = p.compute_gaps(gl)
            assert len(gaps) == 3
            for g in gaps:
                assert "subject" in g
                assert "status" in g


class TestGradeDetailLogDB:
    def test_add_and_retrieve(self, app):
        with app.app_context():
            gl = GradeDetailLogDB(1)
            entry = GradeDetailEntry(
                subject="biology", subject_display="Biology", level="HL",
                command_term="Explain", grade=5, percentage=68,
                mark_earned=3, mark_total=4,
                strengths=["Good"], improvements=["Better examples"],
                examiner_tip="Define terms", topic="Cells",
            )
            gl.add(entry)
            entries = gl.entries
            assert len(entries) >= 1
            assert entries[-1].subject_display == "Biology"

    def test_by_subject(self, app, seeded_grades):
        with app.app_context():
            gl = GradeDetailLogDB(1)
            bio = gl.by_subject("Biology")
            assert len(bio) == 2
            chem = gl.by_subject("Chemistry")
            assert len(chem) == 1

    def test_command_term_stats(self, app, seeded_grades):
        with app.app_context():
            gl = GradeDetailLogDB(1)
            stats = gl.command_term_stats()
            assert "Explain" in stats
            assert stats["Explain"]["count"] == 1

    def test_subject_stats(self, app, seeded_grades):
        with app.app_context():
            gl = GradeDetailLogDB(1)
            stats = gl.subject_stats()
            assert "Biology" in stats
            assert stats["Biology"]["count"] == 2

    def test_recent(self, app, seeded_grades):
        with app.app_context():
            gl = GradeDetailLogDB(1)
            recent = gl.recent(2)
            assert len(recent) == 2


class TestActivityLogDB:
    def test_record_and_streak(self, app):
        with app.app_context():
            al = ActivityLogDB(1)
            al.record("Biology", 5.0, 68.0)
            assert al.days_active_last_n(30) >= 1

    def test_daily_heatmap(self, app):
        with app.app_context():
            al = ActivityLogDB(1)
            al.record("Biology", 5.0, 68.0)
            heatmap = al.daily_heatmap(30)
            assert len(heatmap) == 30
            # Today should have count > 0
            today = date.today().isoformat()
            today_entry = [h for h in heatmap if h["date"] == today]
            assert len(today_entry) == 1
            assert today_entry[0]["count"] > 0


class TestReviewScheduleDB:
    def test_record_and_due(self, app):
        with app.app_context():
            rs = ReviewScheduleDB(1)
            rs.record_review("Biology", "Cells", "Explain", 3)
            # First review sets interval=1, so due tomorrow — check due_this_week instead
            due = rs.due_this_week()
            assert len(due) >= 1

    def test_sm2_interval_growth(self, app):
        with app.app_context():
            rs = ReviewScheduleDB(1)
            # First review (good grade) → interval=1
            rs.record_review("Biology", "DNA", "Describe", 6)
            items = rs.items
            item = [i for i in items if i.topic == "DNA"][0]
            assert item.interval_days == 1

            # Second review → interval=6
            rs.record_review("Biology", "DNA", "Describe", 6)
            items = rs.items
            item = [i for i in items if i.topic == "DNA"][0]
            assert item.interval_days == 6


class TestGamificationProfileDB:
    def test_award_xp(self, app):
        with app.app_context():
            gam = GamificationProfileDB(1)
            result = gam.award_xp(10, "test")
            assert result["xp_earned"] == 10
            assert gam.total_xp >= 10

    def test_level_calculation(self, app):
        with app.app_context():
            gam = GamificationProfileDB(1)
            # Level 1 starts at 0 XP
            assert gam.level >= 1

    def test_check_badges_first_question(self, app):
        with app.app_context():
            gam = GamificationProfileDB(1)
            gam.total_questions_answered = 1
            new = gam.check_badges()
            assert "first_question" in new


class TestFlashcardDeckDB:
    def test_add_and_retrieve(self, app):
        with app.app_context():
            deck = FlashcardDeckDB(1)
            card = Flashcard(id="", front="What is mitosis?", back="Cell division",
                             subject="Biology", topic="Cells")
            deck.add(card)
            assert card.id  # ID should be generated
            assert len(deck.cards) >= 1

    def test_review_sm2(self, app):
        with app.app_context():
            deck = FlashcardDeckDB(1)
            card = Flashcard(id="test_fc_1", front="Q", back="A", subject="Bio")
            deck.add(card)
            deck.review("test_fc_1", 3)  # Good
            cards = deck.cards
            reviewed = [c for c in cards if c.id == "test_fc_1"][0]
            assert reviewed.review_count == 1

    def test_delete(self, app):
        with app.app_context():
            deck = FlashcardDeckDB(1)
            card = Flashcard(id="del_test", front="Q", back="A", subject="Bio")
            deck.add(card)
            assert deck.delete("del_test") is True
            assert deck.delete("nonexistent") is False

    def test_auto_create_from_grade(self, app):
        with app.app_context():
            deck = FlashcardDeckDB(1)
            # Score < 60% should create card
            fc = deck.auto_create_from_grade("Hard Q", "Model A", "Bio", "Topic", 40)
            assert fc is not None
            # Score >= 60% should not
            fc2 = deck.auto_create_from_grade("Easy Q", "Model A", "Bio", "Topic", 80)
            assert fc2 is None


class TestMisconceptionLogDB:
    def test_scan_and_detect(self, app):
        with app.app_context():
            ml = MisconceptionLogDB(1)
            detected = ml.scan_improvements(
                ["Answer was one-sided, needs counter-argument"], "Biology"
            )
            assert "evaluation_weakness" in detected
            misconceptions = ml.active_misconceptions()
            assert len(misconceptions) >= 1


class TestNotificationStoreDB:
    def test_add_and_unread(self, app):
        with app.app_context():
            ns = NotificationStoreDB(1)
            notif = Notification(
                id="test_notif_1", type="flashcard_due",
                title="5 cards due", body="Review them",
                created_at="2026-02-16T10:00:00",
            )
            ns.add(notif)
            assert ns.unread_count() >= 1

    def test_mark_read(self, app):
        with app.app_context():
            ns = NotificationStoreDB(1)
            notif = Notification(
                id="test_notif_2", type="test",
                title="Test", body="Body",
                created_at="2026-02-16T10:00:00",
            )
            ns.add(notif)
            ns.mark_read("test_notif_2")
            # Check it's read
            recent = ns.recent()
            for n in recent:
                if n.id == "test_notif_2":
                    assert n.read is True


class TestStudyPlanDB:
    def test_save_and_load(self, app):
        with app.app_context():
            sp = StudyPlanDB(1)
            tasks = [StudyTask("Biology", "Cells", "practice", 60, "high")]
            plans = [DailyPlan(date=date.today().isoformat(), tasks=tasks, estimated_minutes=60)]
            sp.save("2026-02-16", "2026-05-01", plans)

            loaded = sp.load()
            assert loaded is not None
            assert loaded["generated_date"] == "2026-02-16"
            assert len(loaded["daily_plans"]) == 1
            assert len(loaded["daily_plans"][0].tasks) == 1


class TestWritingProfileDB:
    def test_save_and_load(self, app):
        with app.app_context():
            wp = WritingProfileDB(1)
            wp.save(
                verbosity="Concise",
                terminology_usage="Good",
                argument_structure="Clear",
                common_patterns=["Uses bullet points"],
                summary="A concise writer",
                analyzed_count=1,
            )
            data = wp.load()
            assert data is not None
            assert data["verbosity"] == "Concise"
            assert data["summary"] == "A concise writer"


class TestParentConfigDB:
    def test_generate_token(self, app):
        with app.app_context():
            pc = ParentConfigDB(1)
            token = pc.generate_token()
            assert len(token) == 32  # hex(16) = 32 chars
            assert pc.token == token

    def test_load_by_token(self, app):
        with app.app_context():
            pc = ParentConfigDB(1)
            pc.generate_token()
            pc.save(enabled=True)
            found = ParentConfigDB.load_by_token(pc.token)
            assert found is not None
            assert found.user_id == 1


class TestIBLifecycleDB:
    def test_init_from_profile(self, app):
        with app.app_context():
            lc = IBLifecycleDB(1)
            lc.init_from_profile(["Biology", "Chemistry", "Mathematics: AA"])
            ias = lc.internal_assessments
            assert len(ias) >= 3
            # EE and TOK milestones should exist
            assert lc.total_milestones() > 0

    def test_toggle_milestone(self, app):
        with app.app_context():
            lc = IBLifecycleDB(1)
            lc.init_from_profile(["Biology"])
            ee = lc.extended_essay
            if ee.milestones:
                mid = ee.milestones[0].id
                new_state = lc.toggle_milestone(mid)
                assert new_state is True
                new_state2 = lc.toggle_milestone(mid)
                assert new_state2 is False

    def test_add_cas_reflection(self, app):
        with app.app_context():
            lc = IBLifecycleDB(1)
            reflection = CASReflection(
                strand="Creativity", title="Art project",
                description="Painted a mural", date="2026-02-16",
                learning_outcome="Identify own strengths", hours=5.0,
            )
            lc.add_cas_reflection(reflection)
            assert len(lc.cas_reflections) >= 1
            assert lc.cas_hours["Creativity"] >= 5.0

    def test_summary(self, app):
        with app.app_context():
            lc = IBLifecycleDB(1)
            lc.init_from_profile(["Biology"])
            s = lc.summary()
            assert "total_milestones" in s
            assert "cas_hours" in s


class TestGradeHistoryDB:
    def test_append_and_retrieve(self, app):
        with app.app_context():
            from grader import GradeResult
            gh = GradeHistoryDB(1)
            result = GradeResult(
                question="What is DNA?", answer="A molecule",
                mark_earned=3, mark_total=4, grade=5, percentage=75,
                strengths=["Good"], improvements=["More detail"],
                examiner_tip="Define terms", full_commentary="Solid attempt",
                raw_response="raw", model_answer="Model answer",
            )
            gh.append(result)
            history = gh.history
            assert len(history) >= 1
            assert history[-1]["question"] == "What is DNA?"


class TestUploadStoreDB:
    def test_add_and_load(self, app):
        with app.app_context():
            us = UploadStoreDB(1)
            us.add({
                "id": "upload_1", "filename": "test.pdf",
                "doc_type": "notes", "subject": "Biology",
                "level": "HL", "chunks": 5,
                "uploaded_at": "2026-02-16T10:00:00",
            })
            uploads = us.load()
            assert len(uploads) >= 1
            assert uploads[0]["filename"] == "test.pdf"

    def test_delete(self, app):
        with app.app_context():
            us = UploadStoreDB(1)
            us.add({
                "id": "upload_del", "filename": "del.pdf",
                "doc_type": "notes", "subject": "Bio",
                "level": "HL", "chunks": 1,
                "uploaded_at": "2026-02-16T10:00:00",
            })
            result = us.delete("upload_del")
            assert result is not None
            assert us.delete("nonexistent") is None
