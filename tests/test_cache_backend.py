"""Tests for cache_backend.py — InMemoryCache and RedisCache."""

from __future__ import annotations

import time
import pytest


class TestInMemoryCache:
    def test_set_and_get(self):
        from cache_backend import InMemoryCache
        cache = InMemoryCache()
        cache.set("key1", {"data": "value"}, ttl=60)
        assert cache.get("key1") == {"data": "value"}

    def test_get_missing_key(self):
        from cache_backend import InMemoryCache
        cache = InMemoryCache()
        assert cache.get("nonexistent") is None

    def test_ttl_expiry(self):
        from cache_backend import InMemoryCache
        cache = InMemoryCache()
        cache.set("expiring", "data", ttl=1)
        assert cache.get("expiring") == "data"
        time.sleep(1.1)
        assert cache.get("expiring") is None

    def test_delete(self):
        from cache_backend import InMemoryCache
        cache = InMemoryCache()
        cache.set("to_delete", "value")
        cache.delete("to_delete")
        assert cache.get("to_delete") is None

    def test_clear(self):
        from cache_backend import InMemoryCache
        cache = InMemoryCache()
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_cleanup(self):
        from cache_backend import InMemoryCache
        cache = InMemoryCache()
        cache.set("fresh", "data", ttl=60)
        cache.set("expired", "old", ttl=0)
        time.sleep(0.1)
        removed = cache.cleanup()
        assert removed >= 1
        assert cache.get("fresh") == "data"

    def test_string_values(self):
        from cache_backend import InMemoryCache
        cache = InMemoryCache()
        cache.set("str_key", "just a string", ttl=60)
        assert cache.get("str_key") == "just a string"

    def test_list_values(self):
        from cache_backend import InMemoryCache
        cache = InMemoryCache()
        cache.set("list_key", [1, 2, 3], ttl=60)
        assert cache.get("list_key") == [1, 2, 3]


class TestRedisCache:
    def test_set_and_get(self, fake_redis):
        from cache_backend import RedisCache
        cache = RedisCache(fake_redis)
        cache.set("key1", {"data": "value"}, ttl=60)
        assert cache.get("key1") == {"data": "value"}

    def test_get_missing_key(self, fake_redis):
        from cache_backend import RedisCache
        cache = RedisCache(fake_redis)
        assert cache.get("nonexistent") is None

    def test_delete(self, fake_redis):
        from cache_backend import RedisCache
        cache = RedisCache(fake_redis)
        cache.set("to_delete", "value", ttl=60)
        cache.delete("to_delete")
        assert cache.get("to_delete") is None

    def test_clear(self, fake_redis):
        from cache_backend import RedisCache
        cache = RedisCache(fake_redis)
        cache.set("a", 1, ttl=60)
        cache.set("b", 2, ttl=60)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_cleanup_returns_zero(self, fake_redis):
        from cache_backend import RedisCache
        cache = RedisCache(fake_redis)
        assert cache.cleanup() == 0


class TestInitCache:
    def test_init_without_redis(self, app):
        from cache_backend import init_cache, get_cache, InMemoryCache
        with app.app_context():
            init_cache(app)
            cache = get_cache()
            assert isinstance(cache, InMemoryCache)

    def test_get_cache_lazy_init(self):
        import cache_backend
        # Reset the singleton
        cache_backend._cache = None
        cache = cache_backend.get_cache()
        assert cache is not None
