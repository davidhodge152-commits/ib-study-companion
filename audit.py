"""
Audit logging — records security-relevant events.

Events are written to both the audit_log table and structured logging.
"""

from __future__ import annotations

import logging
from datetime import datetime

from flask import request

from database import get_db

logger = logging.getLogger(__name__)


def log_event(action: str, user_id: int | None = None, detail: str = "") -> None:
    """Insert an audit log entry and emit a structured log line."""
    ip = request.remote_addr or "" if request else ""
    ua = request.headers.get("User-Agent", "") if request else ""
    now = datetime.now().isoformat()

    try:
        db = get_db()
        db.execute(
            "INSERT INTO audit_log (user_id, action, detail, ip_address, user_agent, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, action, detail, ip, ua, now),
        )
        db.commit()
    except Exception:
        pass  # Don't let audit failures break the request

    logger.info("audit: %s user_id=%s detail=%s ip=%s", action, user_id, detail, ip)
