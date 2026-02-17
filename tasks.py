"""Background task processing via RQ with synchronous fallback.

When Redis and RQ are available, tasks are enqueued for a worker process.
Otherwise, tasks execute synchronously in the request thread.

Usage:
    from tasks import enqueue, enqueue_in
    enqueue(some_function, arg1, arg2)
    enqueue_in(60, some_function, arg1)  # delayed by 60 seconds
"""

from __future__ import annotations

import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

_queue = None


def init_tasks(app) -> None:
    """Initialize RQ queue if Redis is available. Call once from create_app()."""
    global _queue

    redis_url = app.config.get("REDIS_URL", "")
    if not redis_url:
        app.logger.info("Task backend: synchronous (no REDIS_URL)")
        return

    try:
        import redis
        from rq import Queue
        conn = redis.Redis.from_url(redis_url)
        conn.ping()
        _queue = Queue(connection=conn)
        app.logger.info("Task backend: RQ (%s)", redis_url)
    except ImportError:
        app.logger.info("Task backend: synchronous (rq not installed)")
    except Exception as e:
        app.logger.warning("Task backend: synchronous (Redis error: %s)", e)


def enqueue(func, *args, **kwargs):
    """Push a task to RQ if available, else call synchronously.

    Returns the RQ Job object or the function's return value.
    """
    if _queue is not None:
        try:
            job = _queue.enqueue(func, *args, **kwargs)
            logger.debug("Enqueued %s (job=%s)", func.__name__, job.id)
            return job
        except Exception as e:
            logger.warning("RQ enqueue failed (%s), falling back to sync: %s", func.__name__, e)

    # Synchronous fallback
    logger.debug("Running %s synchronously", func.__name__)
    return func(*args, **kwargs)


def enqueue_in(delay_seconds: int, func, *args, **kwargs):
    """Push a delayed task to RQ if available, else call synchronously (ignoring delay).

    Returns the RQ Job object or the function's return value.
    """
    if _queue is not None:
        try:
            job = _queue.enqueue_in(timedelta(seconds=delay_seconds), func, *args, **kwargs)
            logger.debug("Enqueued %s with %ds delay (job=%s)", func.__name__, delay_seconds, job.id)
            return job
        except Exception as e:
            logger.warning("RQ enqueue_in failed (%s), falling back to sync: %s", func.__name__, e)

    logger.debug("Running %s synchronously (delay=%ds ignored)", func.__name__, delay_seconds)
    return func(*args, **kwargs)


def is_async_available() -> bool:
    """Check if RQ background processing is available."""
    return _queue is not None
