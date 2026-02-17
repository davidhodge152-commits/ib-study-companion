"""Examiner Review Pipeline — "Final Polish".

Manages the submission, AI pre-analysis, and human examiner review
workflow for student coursework (IAs, EEs, TOK essays).
"""

from __future__ import annotations

import json
from datetime import datetime

from database import get_db


class ExaminerPipeline:
    """Manages the full examiner review lifecycle."""

    def submit_for_review(
        self, user_id: int, doc_type: str, subject: str,
        title: str, text: str,
    ) -> dict:
        """Submit coursework for human examiner review.

        1. Generate AI diagnostic using existing agents
        2. Deduct credits
        3. Insert into examiner_reviews
        4. Return submission confirmation
        """
        # Generate AI diagnostic
        diagnostic = self.generate_ai_diagnostic(text, doc_type, subject)

        # Deduct credits
        from credit_store import CreditStoreDB, FEATURE_COSTS
        store = CreditStoreDB(user_id)
        cost = FEATURE_COSTS.get("examiner_review", 500)
        debit_result = store.debit(cost, "examiner_review",
                                   f"Review: {doc_type} - {title}")
        if not debit_result["success"]:
            return {
                "success": False,
                "error": "Insufficient credits",
                "required": cost,
                "balance": debit_result["balance_after"],
            }

        db = get_db()
        now = datetime.now().isoformat()
        predicted = diagnostic.get("predicted_grade", "")

        cur = db.execute(
            "INSERT INTO examiner_reviews "
            "(user_id, doc_type, subject, title, submission_text, "
            "ai_diagnostic, ai_predicted_grade, status, credits_charged, submitted_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'submitted', ?, ?)",
            (user_id, doc_type, subject, title, text,
             json.dumps(diagnostic), str(predicted), cost, now),
        )
        db.commit()

        return {
            "success": True,
            "review_id": cur.lastrowid,
            "ai_diagnostic": diagnostic,
            "credits_charged": cost,
        }

    def generate_ai_diagnostic(self, text: str, doc_type: str, subject: str) -> dict:
        """Generate structured AI analysis using existing agents.

        Returns a diagnostic dict with criterion scores, strengths,
        improvements, predicted grade, etc.
        """
        diagnostic = {
            "criterion_scores": {},
            "strengths": [],
            "improvements": [],
            "predicted_grade": "",
            "word_count": len(text.split()),
            "formatting_issues": [],
        }

        # Try using CourseworkAgent for review
        try:
            from agents.coursework_agent import CourseworkAgent
            agent = CourseworkAgent(None)
            result = agent.review(
                text=text, doc_type=doc_type, subject=subject,
            )
            if result and result.content:
                diagnostic["ai_review"] = str(result.content)
                if result.metadata and isinstance(result.metadata, dict):
                    diagnostic["criterion_scores"] = result.metadata.get("criteria", {})
                    diagnostic["predicted_grade"] = str(result.metadata.get("grade", ""))
                    diagnostic["strengths"] = result.metadata.get("strengths", [])
                    diagnostic["improvements"] = result.metadata.get("improvements", [])
        except Exception:
            diagnostic["ai_review"] = "AI review unavailable"

        # Word count checks
        limits = {"ia": 2200, "ee": 4000, "tok_essay": 1600}
        limit = limits.get(doc_type, 4000)
        if diagnostic["word_count"] > limit:
            diagnostic["formatting_issues"].append(
                f"Word count ({diagnostic['word_count']}) exceeds recommended limit ({limit})"
            )

        return diagnostic

    @staticmethod
    def assign_to_examiner(review_id: int, examiner_id: int) -> None:
        """Assign a review to an examiner."""
        db = get_db()
        now = datetime.now().isoformat()
        db.execute(
            "UPDATE examiner_reviews SET status = 'assigned', "
            "examiner_id = ?, assigned_at = ? WHERE id = ?",
            (examiner_id, now, review_id),
        )
        db.commit()

    @staticmethod
    def submit_examiner_feedback(
        review_id: int, feedback: str, grade: str,
        video_url: str = "",
    ) -> None:
        """Examiner submits their feedback and grade."""
        db = get_db()
        now = datetime.now().isoformat()
        db.execute(
            "UPDATE examiner_reviews SET status = 'reviewed', "
            "examiner_feedback = ?, examiner_grade = ?, "
            "examiner_video_url = ?, reviewed_at = ? WHERE id = ?",
            (feedback, grade, video_url, now, review_id),
        )
        db.commit()

    @staticmethod
    def deliver_to_student(review_id: int) -> None:
        """Mark review as delivered to student + send notification."""
        db = get_db()
        now = datetime.now().isoformat()
        db.execute(
            "UPDATE examiner_reviews SET status = 'delivered', "
            "delivered_at = ? WHERE id = ?",
            (now, review_id),
        )

        # Notify student
        review = db.execute(
            "SELECT user_id, doc_type, subject, title FROM examiner_reviews WHERE id = ?",
            (review_id,),
        ).fetchone()
        if review:
            try:
                from db_stores import NotificationStoreDB
                from profile import Notification
                import secrets

                notif = NotificationStoreDB(review["user_id"])
                notif.add(Notification(
                    id=secrets.token_hex(8),
                    type="review_delivered",
                    title=f"Your {review['doc_type'].upper()} review is ready!",
                    body=f"An examiner has reviewed your {review['title']}",
                    action_url=f"/reviews/{review_id}",
                ))
            except Exception:
                pass
        db.commit()

    @staticmethod
    def get_review(review_id: int) -> dict | None:
        """Get a review by ID."""
        db = get_db()
        row = db.execute(
            "SELECT * FROM examiner_reviews WHERE id = ?",
            (review_id,),
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        try:
            result["ai_diagnostic"] = json.loads(result["ai_diagnostic"])
        except (json.JSONDecodeError, TypeError):
            pass
        return result

    @staticmethod
    def student_reviews(user_id: int) -> list[dict]:
        """Get all reviews for a student."""
        db = get_db()
        rows = db.execute(
            "SELECT id, doc_type, subject, title, status, ai_predicted_grade, "
            "examiner_grade, submitted_at, delivered_at "
            "FROM examiner_reviews WHERE user_id = ? ORDER BY submitted_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def pending_reviews() -> list[dict]:
        """Get all pending/submitted reviews (examiner queue)."""
        db = get_db()
        rows = db.execute(
            "SELECT er.id, er.doc_type, er.subject, er.title, er.status, "
            "er.ai_predicted_grade, er.submitted_at, u.name as student_name "
            "FROM examiner_reviews er "
            "JOIN users u ON er.user_id = u.id "
            "WHERE er.status IN ('submitted', 'assigned') "
            "ORDER BY er.submitted_at ASC",
        ).fetchall()
        return [dict(r) for r in rows]
