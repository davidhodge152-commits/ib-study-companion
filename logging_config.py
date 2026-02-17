"""
Structured logging configuration.

- JSON format for production (machine-parseable)
- Human-readable text for development
- Request ID middleware for tracing
- Access logging via after_request handler
"""

from __future__ import annotations

import logging
import time
import uuid

from flask import Flask, g, request


class JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        import json

        entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            entry["request_id"] = record.request_id
        if record.exc_info and record.exc_info[0]:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def init_logging(app: Flask) -> None:
    """Configure logging based on app config."""
    log_format = app.config.get("LOG_FORMAT", "text")
    log_level = app.config.get("LOG_LEVEL", "INFO")

    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove default handlers
    root.handlers.clear()

    handler = logging.StreamHandler()
    if log_format == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
    root.addHandler(handler)

    # Quiet noisy libraries
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    # Request ID middleware
    @app.before_request
    def _attach_request_id():
        g.request_id = uuid.uuid4().hex[:12]
        g.request_start = time.time()

    # Access logging
    @app.after_request
    def _log_request(response):
        if request.path.startswith("/static"):
            return response
        duration_ms = (time.time() - getattr(g, "request_start", time.time())) * 1000
        app.logger.info(
            "%s %s %s %.0fms",
            request.method,
            request.path,
            response.status_code,
            duration_ms,
            extra={"request_id": getattr(g, "request_id", "-")},
        )
        return response
