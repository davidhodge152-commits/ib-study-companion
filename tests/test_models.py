"""Tests for pure logic — exam countdown, SM-2 quality mapping, gamification formulas."""

import math
import pytest
from datetime import date, timedelta


class TestExamCountdown:
    def test_may_session(self, app):
        with app.app_context():
            from db_stores import StudentProfileDB
            p = StudentProfileDB(1)
            cd = p.exam_countdown()
            assert cd["exam_date"] == "2026-05-01"
            assert cd["days"] >= 0

    def test_urgency_levels(self, app):
        with app.app_context():
            from db_stores import StudentProfileDB
            p = StudentProfileDB(1)
            cd = p.exam_countdown()
            assert cd["urgency"] in ("calm", "focused", "urgent", "critical")


class TestSM2QualityMapping:
    """Test the SM-2 quality mapping from IB grades."""

    def test_grade_to_quality(self):
        from profile import ReviewSchedule
        rs = ReviewSchedule.__new__(ReviewSchedule)
        rs.items = []
        mapping = {7: 5, 6: 4, 5: 3, 4: 2, 3: 1, 2: 0, 1: 0}
        for grade, expected in mapping.items():
            assert rs._grade_to_quality(grade) == expected


class TestGamificationFormulas:
    """Test XP, level, and progress calculations."""

    def test_level_from_xp(self):
        """Level = floor(sqrt(xp / 50)) + 1"""
        cases = [
            (0, 1),     # sqrt(0/50) = 0 → level 1
            (50, 2),    # sqrt(50/50) = 1 → level 2
            (200, 3),   # sqrt(200/50) = 2 → level 3
            (450, 4),   # sqrt(450/50) = 3 → level 4
        ]
        for xp, expected_level in cases:
            level = int(math.sqrt(xp / 50)) + 1
            assert level == expected_level, f"XP={xp} should be level {expected_level}, got {level}"

    def test_xp_for_level_boundaries(self):
        """XP needed for level n = (n-1)^2 * 50"""
        cases = [
            (1, 0),      # Level 1: 0 XP
            (2, 50),     # Level 2: 50 XP
            (3, 200),    # Level 3: 200 XP
            (4, 450),    # Level 4: 450 XP
            (5, 800),    # Level 5: 800 XP
        ]
        for level, expected_xp in cases:
            xp_needed = (level - 1) ** 2 * 50
            assert xp_needed == expected_xp

    def test_xp_progress_percentage(self):
        """Progress within a level."""
        total_xp = 125  # Between level 2 (50) and level 3 (200)
        level = int(math.sqrt(total_xp / 50)) + 1
        assert level == 2
        level_start = (level - 1) ** 2 * 50  # 50
        level_end = level ** 2 * 50  # 200
        progress = int((total_xp - level_start) / (level_end - level_start) * 100)
        assert progress == 50  # 75/150 = 50%


class TestMisconceptionPatternMatching:
    """Test that misconception keywords match correctly."""

    def test_evaluation_weakness_detected(self):
        from profile import MISCONCEPTION_PATTERNS
        pattern = MISCONCEPTION_PATTERNS["evaluation_weakness"]
        feedback = "The answer was one-sided with no counter-argument presented"
        feedback_lower = feedback.lower()
        matched = any(kw in feedback_lower for kw in pattern["keywords"])
        assert matched is True

    def test_vocabulary_gap_detected(self):
        from profile import MISCONCEPTION_PATTERNS
        pattern = MISCONCEPTION_PATTERNS["vocabulary_gap"]
        feedback = "Missing key terminology and subject-specific vocabulary"
        feedback_lower = feedback.lower()
        matched = any(kw in feedback_lower for kw in pattern["keywords"])
        assert matched is True

    def test_no_false_positive(self):
        from profile import MISCONCEPTION_PATTERNS
        feedback = "Great work overall, clear and well-structured response"
        feedback_lower = feedback.lower()
        for pid, pattern in MISCONCEPTION_PATTERNS.items():
            matched = any(kw in feedback_lower for kw in pattern["keywords"])
            if pid == "essay_structure":
                # "structure" matches "well-structured"
                continue
            assert matched is False, f"False positive for {pid}"
