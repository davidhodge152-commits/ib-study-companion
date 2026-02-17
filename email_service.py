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
        """Send an email (background if RQ available, else inline).

        Returns True on success (or True if enqueued).
        """
        backend = current_app.config.get("EMAIL_BACKEND", "log")

        if backend == "log":
            logger.info(
                "EMAIL [to=%s] subject=%s\n%s",
                to, subject, body_html,
            )
            return True

        # Extract config for context-free background execution
        config = {
            "mail_from": current_app.config.get("MAIL_FROM", "noreply@example.com"),
            "mail_server": current_app.config.get("MAIL_SERVER", "localhost"),
            "mail_port": current_app.config.get("MAIL_PORT", 587),
            "mail_username": current_app.config.get("MAIL_USERNAME", ""),
            "mail_password": current_app.config.get("MAIL_PASSWORD", ""),
        }

        try:
            from tasks import enqueue
            enqueue(EmailService._do_send, to, subject, body_html, config)
            return True
        except Exception:
            return EmailService._do_send(to, subject, body_html, config)

    @staticmethod
    def _do_send(to: str, subject: str, body_html: str, config: dict) -> bool:
        """Actual SMTP send — no Flask context required."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = config.get("mail_from", "noreply@example.com")
            msg["To"] = to
            msg.attach(MIMEText(body_html, "html"))

            server = config.get("mail_server", "localhost")
            port = config.get("mail_port", 587)
            username = config.get("mail_username", "")
            password = config.get("mail_password", "")

            with smtplib.SMTP(server, port) as smtp:
                smtp.starttls()
                if username and password:
                    smtp.login(username, password)
                smtp.send_message(msg)
            return True
        except Exception as e:
            logger.error("SMTP send failed: %s", e)
            return False
