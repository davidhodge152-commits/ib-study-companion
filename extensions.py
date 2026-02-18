"""
Singleton management for expensive objects (RAG engine, grader) and rate limiter.

Replaces the nonlocal closure pattern from create_app().
"""

from __future__ import annotations

import os


def _create_limiter():
    """Create a real Limiter or a no-op stub depending on environment."""
    if os.environ.get("VERCEL"):
        # On Vercel, rate limiting is useless (no shared state between invocations).
        # Return a lightweight stub to avoid importing flask_limiter (~200ms).
        class _NoOpLimiter:
            enabled = False
            def init_app(self, app): pass
            def limit(self, *a, **kw):
                def decorator(f): return f
                return decorator
        return _NoOpLimiter()

    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    return Limiter(key_func=get_remote_address, default_limits=["200 per hour"])


limiter = _create_limiter()


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
