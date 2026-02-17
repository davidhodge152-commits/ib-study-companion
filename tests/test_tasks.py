"""Tests for tasks.py — synchronous fallback and enqueue wrapper."""

from __future__ import annotations

import pytest


def _sample_task(x, y):
    """A simple function for testing enqueue."""
    return x + y


def _sample_task_with_kwargs(x, multiplier=1):
    return x * multiplier


class TestSynchronousFallback:
    def test_enqueue_runs_sync_without_redis(self):
        from tasks import enqueue
        # Without RQ/Redis, enqueue should call synchronously
        result = enqueue(_sample_task, 3, 4)
        assert result == 7

    def test_enqueue_in_runs_sync_without_redis(self):
        from tasks import enqueue_in
        result = enqueue_in(10, _sample_task, 5, 6)
        assert result == 11

    def test_enqueue_with_kwargs(self):
        from tasks import enqueue
        result = enqueue(_sample_task_with_kwargs, 3, multiplier=5)
        assert result == 15


class TestIsAsyncAvailable:
    def test_returns_false_without_redis(self):
        from tasks import is_async_available
        # By default (no REDIS_URL), should be False
        assert is_async_available() is False


class TestInitTasks:
    def test_init_without_redis_url(self, app):
        from tasks import init_tasks, is_async_available
        with app.app_context():
            init_tasks(app)
            assert is_async_available() is False

    def test_init_with_invalid_redis_url(self, app):
        from tasks import init_tasks, is_async_available
        app.config["REDIS_URL"] = "redis://invalid-host:9999"
        with app.app_context():
            init_tasks(app)
            # Should fall back gracefully
            assert is_async_available() is False
