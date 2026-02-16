"""Tests for enhanced RAG: examiner report parsing, mark scheme parsing, metadata."""

from __future__ import annotations

import sys
import pytest
from unittest.mock import MagicMock

# Mock chromadb before importing ingest (it's imported at module level)
if "chromadb" not in sys.modules:
    sys.modules["chromadb"] = MagicMock()
if "pypdf" not in sys.modules:
    sys.modules["pypdf"] = MagicMock()


class TestExaminerReportParsing:
    def test_parse_examiner_report_basic(self):
        from ingest import parse_examiner_report

        text = """
Question 1
Topic: Cell Biology
Many candidates failed to define osmosis correctly.
60% of students lost marks because they did not mention a partially permeable membrane.
Candidates should always include the key terminology in their definitions.

Question 2
Topic: Molecular Biology
Most candidates answered well.
Common error: confusing transcription with translation.
Students are advised to draw a clear diagram to distinguish the two processes.
"""
        entries = parse_examiner_report(text)
        assert len(entries) == 2
        assert entries[0]["question_num"] == "1"
        assert entries[0]["topic"] == "Cell Biology"
        assert len(entries[0]["common_errors"]) >= 1
        assert entries[0]["marks_lost_pct"] == 60
        assert "terminology" in entries[0]["examiner_advice"]

        assert entries[1]["question_num"] == "2"
        assert len(entries[1]["common_errors"]) >= 1

    def test_parse_examiner_report_empty(self):
        from ingest import parse_examiner_report

        assert parse_examiner_report("") == []
        assert parse_examiner_report("Some random text without questions") == []

    def test_parse_examiner_report_q_format(self):
        from ingest import parse_examiner_report

        text = """
Q3
Common error: students often forgot to include units.
"""
        entries = parse_examiner_report(text)
        assert len(entries) == 1
        assert entries[0]["question_num"] == "3"


class TestMarkSchemeParsing:
    def test_parse_mark_scheme_basic(self):
        from ingest import parse_mark_scheme

        text = """
Question 1 [4 marks]
- M1 correct substitution into formula
- A1 correct calculation
- M1 appropriate units
- A1 final answer with correct significant figures

Question 2a
(3 marks)
- Define osmosis correctly
- Mention partially permeable membrane
- Reference to concentration gradient
"""
        entries = parse_mark_scheme(text)
        assert len(entries) == 2
        assert entries[0]["question_num"] == "1"
        assert entries[0]["marks"] == 4  # From mark codes count
        assert "M1" in entries[0]["mark_types"]
        assert "A1" in entries[0]["mark_types"]
        assert len(entries[0]["criteria"]) >= 2

        assert entries[1]["question_num"] == "2a"
        assert entries[1]["marks"] == 3

    def test_parse_mark_scheme_empty(self):
        from ingest import parse_mark_scheme

        assert parse_mark_scheme("") == []

    def test_parse_mark_scheme_with_codes(self):
        from ingest import parse_mark_scheme

        text = """
Question 5
M1 for using correct formula
A1 for correct numerical answer
R1 for stating the conclusion
"""
        entries = parse_mark_scheme(text)
        assert len(entries) == 1
        assert "M1" in entries[0]["mark_types"]
        assert "A1" in entries[0]["mark_types"]
        assert "R1" in entries[0]["mark_types"]


class TestEnhancedMetadata:
    def test_detect_year(self):
        from ingest import detect_year

        assert detect_year("biology_2024_paper1.pdf", "") == 2024
        assert detect_year("test.pdf", "May 2023 examination session") == 2023
        assert detect_year("unknown.pdf", "no year here") == 0

    def test_detect_session(self):
        from ingest import detect_session

        assert detect_session("biology_may_2024.pdf", "") == "May"
        assert detect_session("", "November 2023 examination") == "Nov"
        assert detect_session("test.pdf", "no session") == ""

    def test_detect_paper_number(self):
        from ingest import detect_paper_number

        assert detect_paper_number("biology_paper2.pdf", "") == 2
        assert detect_paper_number("", "Paper 1 Section A") == 1
        assert detect_paper_number("notes.pdf", "no paper") == 0

    def test_classify_examiner_report(self):
        from ingest import classify_document

        # Examiner reports don't have a specific classifier yet,
        # but the existing classifier should handle mark scheme detection
        assert classify_document("markscheme_bio.pdf", "markband criteria") == "mark_scheme"
        assert classify_document("paper1_2024.pdf", "Question 1") == "past_paper"
        assert classify_document("guide.pdf", "syllabus content aims") == "subject_guide"
