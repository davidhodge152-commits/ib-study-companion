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

    # 3. Monthly credit allocation — daily check at 1 AM
    def _allocate_monthly_credits():
        with app.app_context():
            try:
                from database import get_db
                from datetime import datetime, date
                db = get_db()
                today = date.today().isoformat()
                # Find active subscribers whose last_allocation_date is not today
                rows = db.execute(
                    "SELECT cb.user_id, cb.monthly_allocation, cb.balance "
                    "FROM credit_balances cb "
                    "JOIN user_subscriptions us ON cb.user_id = us.user_id "
                    "WHERE us.status = 'active' "
                    "AND cb.monthly_allocation > 0 "
                    "AND (cb.last_allocation_date < ? OR cb.last_allocation_date = '')",
                    (today[:7],),  # Compare month prefix (YYYY-MM)
                ).fetchall()
                for r in rows:
                    new_balance = r["balance"] + r["monthly_allocation"]
                    db.execute(
                        "UPDATE credit_balances SET balance = ?, last_allocation_date = ? "
                        "WHERE user_id = ?",
                        (new_balance, today, r["user_id"]),
                    )
                    db.execute(
                        "INSERT INTO credit_transactions (user_id, amount, type, feature, "
                        "description, balance_after, created_at) "
                        "VALUES (?, ?, 'allocation', 'monthly', 'Monthly credit allocation', ?, ?)",
                        (r["user_id"], r["monthly_allocation"], new_balance,
                         datetime.now().isoformat()),
                    )
                db.commit()
                if rows:
                    app.logger.info("Allocated monthly credits for %d subscribers", len(rows))
            except Exception as e:
                app.logger.error("Credit allocation failed: %s", e)

    scheduler.add_job(
        func=_allocate_monthly_credits,
        trigger="cron",
        hour=1,
        id="monthly_credits",
        replace_existing=True,
    )

    # 4. TTL cache cleanup — every 1 hour
    def _cleanup_cache():
        try:
            from cache_backend import get_cache
            get_cache().cleanup()
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
