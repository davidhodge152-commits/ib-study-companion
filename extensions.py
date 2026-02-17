"""
Singleton management for expensive objects (RAG engine, grader) and rate limiter.

Replaces the nonlocal closure pattern from create_app().
"""

from __future__ import annotations

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per hour"],
    storage_uri="memory://",
)


class EngineManager:
    """Lazy-loaded singletons for RAGEngine and IBGrader."""

    _engine = None
    _grader = None

    @classmethod
    def get_engine(cls):
        if cls._engine is None:
            from rag_engine import RAGEngine
            cls._engine = RAGEngine()
        return cls._engine

    @classmethod
    def get_grader(cls):
        if cls._grader is None:
            from grader import IBGrader
            cls._grader = IBGrader(cls.get_engine())
        return cls._grader

    @classmethod
    def reset(cls):
        """Reset both singletons — called after upload/delete doc."""
        cls._engine = None
        cls._grader = None
