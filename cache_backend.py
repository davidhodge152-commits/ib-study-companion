"""Unified caching interface with Redis / in-memory swap.

Provides a simple get/set/delete/clear API. When REDIS_URL is configured
and the redis package is installed, uses Redis; otherwise falls back to the
in-memory TTLCache from ai_resilience.py.

Usage:
    from cache_backend import init_cache, get_cache
    init_cache(app)          # called once in create_app()
    cache = get_cache()      # module-level accessor
    cache.set("key", value, ttl=300)
    value = cache.get("key")
"""

from __future__ import annotations

import json
import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)

# ── Protocol ───────────────────────────────────────────────

class CacheBackend(Protocol):
    def get(self, key: str) -> Any | None: ...
    def set(self, key: str, value: Any, ttl: int = 300) -> None: ...
    def delete(self, key: str) -> None: ...
    def clear(self) -> None: ...
    def cleanup(self) -> int: ...


# ── In-Memory Implementation ──────────────────────────────

class InMemoryCache:
    """Wraps the existing TTLCache from ai_resilience.py."""

    def __init__(self) -> None:
        from ai_resilience import TTLCache
        self._store = TTLCache()

    def get(self, key: str) -> Any | None:
        raw = self._store.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        raw = json.dumps(value) if not isinstance(value, str) else value
        self._store.set(key, raw, ttl)

    def delete(self, key: str) -> None:
        with self._store._lock:
            self._store._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()

    def cleanup(self) -> int:
        return self._store.cleanup()


# ── Redis Implementation ──────────────────────────────────

class RedisCache:
    """Wraps redis.Redis with graceful error handling."""

    def __init__(self, redis_client) -> None:
        self._redis = redis_client

    def get(self, key: str) -> Any | None:
        try:
            raw = self._redis.get(key)
            if raw is None:
                return None
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return raw.decode() if isinstance(raw, bytes) else raw
        except Exception as e:
            logger.warning("Redis GET error (key=%s): %s", key, e)
            return None

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        try:
            raw = json.dumps(value) if not isinstance(value, str) else value
            self._redis.setex(key, ttl, raw)
        except Exception as e:
            logger.warning("Redis SET error (key=%s): %s", key, e)

    def delete(self, key: str) -> None:
        try:
            self._redis.delete(key)
        except Exception as e:
            logger.warning("Redis DELETE error (key=%s): %s", key, e)

    def clear(self) -> None:
        try:
            self._redis.flushdb()
        except Exception as e:
            logger.warning("Redis CLEAR error: %s", e)

    def cleanup(self) -> int:
        # Redis handles expiry natively
        return 0


# ── Module-level singleton ────────────────────────────────

_cache: CacheBackend | None = None


def init_cache(app) -> None:
    """Initialize the cache backend. Call once from create_app()."""
    global _cache

    redis_url = app.config.get("REDIS_URL", "")
    if redis_url:
        try:
            import redis
            client = redis.Redis.from_url(redis_url, decode_responses=False)
            client.ping()
            _cache = RedisCache(client)
            app.logger.info("Cache backend: Redis (%s)", redis_url)
            return
        except ImportError:
            app.logger.info("redis package not installed — falling back to in-memory cache.")
        except Exception as e:
            app.logger.warning("Redis connection failed (%s) — falling back to in-memory cache.", e)

    _cache = InMemoryCache()
    app.logger.info("Cache backend: in-memory (TTLCache)")


def get_cache() -> CacheBackend:
    """Return the active cache backend. Lazily initializes if needed."""
    global _cache
    if _cache is None:
        _cache = InMemoryCache()
    return _cache
