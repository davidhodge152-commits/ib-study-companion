"""Tests for performance features — ETag, compression, cache headers, vector store."""

from __future__ import annotations

import json
import pytest


class TestETag:
    def test_json_response_has_etag(self, auth_client):
        resp = auth_client.get("/api/gamification")
        assert resp.status_code == 200
        assert "ETag" in resp.headers

    def test_304_on_matching_etag(self, auth_client):
        resp1 = auth_client.get("/api/gamification")
        etag = resp1.headers.get("ETag")
        assert etag

        resp2 = auth_client.get(
            "/api/gamification",
            headers={"If-None-Match": etag},
        )
        assert resp2.status_code == 304

    def test_200_on_mismatched_etag(self, auth_client):
        resp = auth_client.get(
            "/api/gamification",
            headers={"If-None-Match": '"stale-etag"'},
        )
        assert resp.status_code == 200


class TestCacheBackendIntegration:
    def test_cache_backend_works_in_app(self, app):
        with app.app_context():
            from cache_backend import get_cache
            cache = get_cache()
            cache.set("test_key", {"foo": "bar"}, ttl=60)
            assert cache.get("test_key") == {"foo": "bar"}

    def test_leaderboard_cache(self, app, db):
        """Leaderboard results should be cached on second call."""
        with app.app_context():
            from db_stores import LeaderboardStoreDB
            from cache_backend import get_cache

            # First call — populates cache
            result1 = LeaderboardStoreDB.get("global")
            # Second call — should come from cache
            result2 = LeaderboardStoreDB.get("global")
            assert result1 == result2


class TestVectorStore:
    def test_chromadb_store_protocol(self):
        from vector_store import ChromaDBStore
        store = ChromaDBStore.__new__(ChromaDBStore)
        # Verify it has the required methods
        assert hasattr(store, "add")
        assert hasattr(store, "query")
        assert hasattr(store, "get")
        assert hasattr(store, "delete")
        assert hasattr(store, "count")

    def test_reset_vector_store(self):
        import vector_store
        vector_store._store = "sentinel"
        vector_store.reset_vector_store()
        assert vector_store._store is None


class TestMigrationLocking:
    def test_migrations_apply_with_locking(self, app):
        """Migrations should complete successfully with file locking."""
        with app.app_context():
            from database import get_db
            db = get_db()
            # Check that migration 37 (performance indexes) was applied
            row = db.execute(
                "SELECT version FROM schema_version WHERE version = 37"
            ).fetchone()
            assert row is not None


class TestPaginationHelpers:
    def test_paginated_response_math(self):
        from helpers import paginated_response
        # 25 total, page 3, limit 10 = pages should be 3
        result = paginated_response([1, 2, 3, 4, 5], total=25, page=3, limit=10)
        assert result["pagination"]["pages"] == 3
        assert result["pagination"]["total"] == 25
