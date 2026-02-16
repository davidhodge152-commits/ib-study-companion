"""Syllabus Knowledge Graph — prerequisite DAG + mastery states.

Models the IB syllabus as a directed acyclic graph where edges represent
prerequisite relationships. Combined with Bayesian Knowledge Tracing to
track student mastery and recommend optimal study paths.
"""

from __future__ import annotations

from collections import deque

from database import get_db
from subject_config import get_syllabus_topics


# Mastery state thresholds
MASTERY_THRESHOLDS = {
    "mastered": {"theta_min": 0.5, "uncertainty_max": 0.3, "attempts_min": 5},
    "partial": {"theta_min": -0.3},
    "learning": {"theta_max": -0.3, "uncertainty_min": 0.5},
}


def compute_mastery(
    theta: float, uncertainty: float, attempts: int, correct_ratio: float
) -> str:
    """Compute mastery state from ability parameters.

    States:
        unknown  — Never attempted
        learning — Attempted but low mastery
        partial  — Some understanding
        mastered — Strong understanding
    """
    if attempts == 0:
        return "unknown"
    if theta < -0.3 or uncertainty > 0.5:
        return "learning"
    if theta > 0.5 and uncertainty < 0.3 and attempts >= 5:
        return "mastered"
    return "partial"


class SyllabusGraph:
    """Prerequisite DAG for a single IB subject."""

    def __init__(self, subject: str) -> None:
        self.subject = subject
        self._topics = get_syllabus_topics(subject)
        self._topic_ids = {t.id for t in self._topics}

    def get_prerequisites(self, topic_id: str) -> list[str]:
        """Return topic_ids that must be mastered before this one."""
        db = get_db()
        rows = db.execute(
            "SELECT requires_topic_id FROM topic_prerequisites "
            "WHERE subject = ? AND topic_id = ?",
            (self.subject, topic_id),
        ).fetchall()
        return [r["requires_topic_id"] for r in rows]

    def get_dependents(self, topic_id: str) -> list[str]:
        """Return topic_ids that depend on this one."""
        db = get_db()
        rows = db.execute(
            "SELECT topic_id FROM topic_prerequisites "
            "WHERE subject = ? AND requires_topic_id = ?",
            (self.subject, topic_id),
        ).fetchall()
        return [r["topic_id"] for r in rows]

    def get_mastery_map(self, user_id: int) -> dict:
        """Return mastery state for every topic in this subject.

        Returns:
            {topic_id: {name, state, theta, uncertainty, attempts,
                        prerequisites_met, hl_only}}
        """
        db = get_db()
        mastery: dict = {}

        for topic in self._topics:
            # Get ability data
            row = db.execute(
                "SELECT theta, uncertainty, attempts, mastery_state, last_correct_ratio "
                "FROM student_ability WHERE user_id = ? AND subject = ? AND topic = ?",
                (user_id, self.subject, topic.name),
            ).fetchone()

            if row:
                theta = row["theta"]
                uncertainty = row["uncertainty"]
                attempts = row["attempts"]
                correct_ratio = row["last_correct_ratio"] or 0.0
                state = compute_mastery(theta, uncertainty, attempts, correct_ratio)
            else:
                theta = 0.0
                uncertainty = 1.0
                attempts = 0
                correct_ratio = 0.0
                state = "unknown"

            # Check if prerequisites are met
            prereqs = self.get_prerequisites(topic.id)
            prereqs_met = True
            for prereq_id in prereqs:
                prereq_topic = self._find_topic_name(prereq_id)
                if prereq_topic:
                    prereq_row = db.execute(
                        "SELECT theta, uncertainty, attempts "
                        "FROM student_ability "
                        "WHERE user_id = ? AND subject = ? AND topic = ?",
                        (user_id, self.subject, prereq_topic),
                    ).fetchone()
                    if not prereq_row or compute_mastery(
                        prereq_row["theta"],
                        prereq_row["uncertainty"],
                        prereq_row["attempts"],
                        0.0,
                    ) not in ("mastered", "partial"):
                        prereqs_met = False
                        break

            mastery[topic.id] = {
                "name": topic.name,
                "state": state,
                "theta": round(theta, 3),
                "uncertainty": round(uncertainty, 3),
                "attempts": attempts,
                "prerequisites_met": prereqs_met,
                "hl_only": topic.hl_only,
            }

        return mastery

    def get_recommended_next(self, user_id: int, limit: int = 5) -> list[dict]:
        """BFS from mastered nodes to find optimal next topics.

        Prioritizes: prerequisites met + lowest mastery + highest exam weight.
        """
        mastery_map = self.get_mastery_map(user_id)

        candidates: list[dict] = []
        for topic_id, info in mastery_map.items():
            # Skip already mastered topics
            if info["state"] == "mastered":
                continue
            # Only recommend topics whose prerequisites are met
            if not info["prerequisites_met"]:
                continue
            # Prioritize: lower theta = more need, more attempts = more investment
            priority = -info["theta"] + (0.1 if info["state"] == "learning" else 0)
            candidates.append({
                "topic_id": topic_id,
                "name": info["name"],
                "state": info["state"],
                "theta": info["theta"],
                "priority": round(priority, 3),
            })

        # Sort by priority (highest first = most needing study)
        candidates.sort(key=lambda x: x["priority"], reverse=True)
        return candidates[:limit]

    def _find_topic_name(self, topic_id: str) -> str | None:
        """Find topic name by ID."""
        for t in self._topics:
            if t.id == topic_id:
                return t.name
        return None

    def get_learning_path(self, target_topic_id: str, user_id: int) -> list[str]:
        """Return ordered list of topic_ids to study to reach a target topic.

        Uses reverse BFS from target to find all unmastered prerequisites.
        """
        mastery_map = self.get_mastery_map(user_id)
        path: list[str] = []
        visited: set[str] = set()
        queue = deque([target_topic_id])

        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)

            info = mastery_map.get(current)
            if info and info["state"] != "mastered":
                path.append(current)

            # Add prerequisites to explore
            for prereq in self.get_prerequisites(current):
                if prereq not in visited:
                    queue.append(prereq)

        # Reverse so prerequisites come first
        path.reverse()
        return path
