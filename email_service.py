"""
Email service — sends email via SMTP or logs to console.

Uses EMAIL_BACKEND config to choose transport:
  - "log" (default): prints email to console/log
  - "smtp": sends via SMTP using MAIL_* settings
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import current_app

logger = logging.getLogger(__name__)


class EmailService:
    @staticmethod
    def send(to: str, subject: str, body_html: str) -> bool:
        """Send an email. Returns True on success."""
        backend = current_app.config.get("EMAIL_BACKEND", "log")

        if backend == "smtp":
            return EmailService._send_smtp(to, subject, body_html)

        # Default: log to console
        logger.info(
            "EMAIL [to=%s] subject=%s\n%s",
            to, subject, body_html,
        )
        return True

    @staticmethod
    def _send_smtp(to: str, subject: str, body_html: str) -> bool:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = current_app.config.get("MAIL_FROM", "noreply@example.com")
            msg["To"] = to
            msg.attach(MIMEText(body_html, "html"))

            server = current_app.config.get("MAIL_SERVER", "localhost")
            port = current_app.config.get("MAIL_PORT", 587)
            username = current_app.config.get("MAIL_USERNAME", "")
            password = current_app.config.get("MAIL_PASSWORD", "")

            with smtplib.SMTP(server, port) as smtp:
                smtp.starttls()
                if username and password:
                    smtp.login(username, password)
                smtp.send_message(msg)
            return True
        except Exception as e:
            logger.error("SMTP send failed: %s", e)
            return False
