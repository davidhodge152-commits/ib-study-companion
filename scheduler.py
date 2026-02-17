"""
Centralized Scheduler — Registers all periodic background jobs.

Jobs:
  - Push study reminders (every 4 hours)
  - Daily analytics aggregation (2 AM)
  - TTL cache cleanup (every 1 hour)
"""

from __future__ import annotations


def init_scheduler(app):
    """Start a centralized background scheduler for all periodic jobs.

    Uses APScheduler if available. Returns the scheduler instance or None.
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        app.logger.info("APScheduler not installed — scheduling disabled.")
        return None

    scheduler = BackgroundScheduler(daemon=True)

    # 1. Push study reminders — every 4 hours
    from push import send_study_reminders
    scheduler.add_job(
        func=send_study_reminders,
        args=[app],
        trigger="interval",
        hours=4,
        id="study_reminders",
        replace_existing=True,
    )

    # 2. Daily analytics aggregation — cron at 2 AM
    from data_pipeline import aggregate_daily_analytics
    scheduler.add_job(
        func=aggregate_daily_analytics,
        args=[app],
        trigger="cron",
        hour=2,
        id="daily_analytics",
        replace_existing=True,
    )

    # 3. TTL cache cleanup — every 1 hour
    def _cleanup_cache():
        try:
            from ai_resilience import _cache
            _cache.cleanup()
        except Exception:
            pass

    scheduler.add_job(
        func=_cleanup_cache,
        trigger="interval",
        hours=1,
        id="cache_cleanup",
        replace_existing=True,
    )

    scheduler.start()
    app.logger.info("Centralized scheduler started (reminders, analytics, cache cleanup)")
    return scheduler
