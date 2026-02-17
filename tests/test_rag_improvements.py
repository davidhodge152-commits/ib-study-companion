"""Tests for RAG engine enhancements: hybrid search, chunk validation, citations."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

# Mock chromadb and pypdf before importing modules that use them at module level
if "chromadb" not in sys.modules:
    sys.modules["chromadb"] = MagicMock()
if "pypdf" not in sys.modules:
    sys.modules["pypdf"] = MagicMock()

import pytest

from ingest import validate_chunk, chunk_text
from rag_engine import RetrievedChunk


class TestChunkValidation:
    def test_valid_chunk(self):
        text = "This is a perfectly valid chunk of text about IB Biology that discusses photosynthesis."
        valid, reason = validate_chunk(text)
        assert valid is True
        assert reason == ""

    def test_too_short(self):
        valid, reason = validate_chunk("short")
        assert valid is False
        assert "too short" in reason

    def test_too_long(self):
        valid, reason = validate_chunk("a" * 4001)
        assert valid is False
        assert "too long" in reason

    def test_low_alpha_ratio(self):
        text = "1234567890 !@#$%^&*() 12345 67890 !@#$% ^&*() more numbers 12345"
        valid, reason = validate_chunk(text)
        assert valid is False
        assert "alpha ratio" in reason

    def test_valid_with_mixed_content(self):
        text = (
            "Question 3(a) [6 marks]: Explain the process of DNA replication. "
            "Include at least three key steps and reference the role of helicase "
            "and DNA polymerase in the process."
        )
        valid, reason = validate_chunk(text)
        assert valid is True

    def test_empty_string(self):
        valid, reason = validate_chunk("")
        assert valid is False


class TestRetrievedChunkDataclass:
    def test_new_fields_default(self):
        chunk = RetrievedChunk(
            text="test", source="test.pdf", doc_type="past_paper",
            subject="biology", level="HL", distance=0.5,
        )
        assert chunk.keyword_score == 0.0
        assert chunk.relevance_score == 0.0

    def test_new_fields_set(self):
        chunk = RetrievedChunk(
            text="test", source="test.pdf", doc_type="past_paper",
            subject="biology", level="HL", distance=0.5,
            keyword_score=0.8, relevance_score=0.75,
        )
        assert chunk.keyword_score == 0.8
        assert chunk.relevance_score == 0.75


class TestMigration34:
    def test_rag_citations_table_exists(self, app):
        with app.app_context():
            from database import get_db
            db = get_db()
            row = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='rag_citations'"
            ).fetchone()
            assert row is not None


class TestRAGCitationStoreDB:
    def test_record_and_retrieve(self, app):
        with app.app_context():
            from db_stores import RAGCitationStoreDB, AgentInteractionStoreDB

            iid = AgentInteractionStoreDB.log(
                user_id=1, intent="explain_concept", agent="tutor_agent",
                confidence=0.9, input_summary="test", response_summary="test",
                latency_ms=100,
            )
            assert iid is not None

            chunks = [
                RetrievedChunk(
                    text="Photosynthesis is the process...",
                    source="biology_paper.pdf",
                    doc_type="past_paper",
                    subject="biology",
                    level="HL",
                    distance=0.3,
                    relevance_score=0.7,
                ),
            ]

            RAGCitationStoreDB.record(iid, 1, chunks)
            citations = RAGCitationStoreDB.get_for_interaction(iid)
            assert len(citations) == 1
            assert citations[0]["chunk_source"] == "biology_paper.pdf"

    def test_source_usage_stats(self, app):
        with app.app_context():
            from db_stores import RAGCitationStoreDB
            stats = RAGCitationStoreDB.source_usage_stats()
            assert isinstance(stats, list)


class TestChunkTextIntegration:
    def test_chunk_text_produces_valid_chunks(self):
        text = (
            "Question 1\n\n"
            "Explain the process of natural selection. Natural selection is a "
            "key mechanism of evolution. It acts on the phenotype of organisms. "
            "Organisms with traits better suited to their environment tend to "
            "survive and reproduce more successfully.\n\n"
            "Question 2\n\n"
            "Describe the structure of DNA. DNA is a double helix composed of "
            "two polynucleotide chains. Each nucleotide consists of a phosphate "
            "group, deoxyribose sugar, and a nitrogenous base."
        )
        chunks = chunk_text(text)
        for c in chunks:
            valid, _ = validate_chunk(c)
            assert valid, f"Chunk failed validation: {c[:50]}..."
