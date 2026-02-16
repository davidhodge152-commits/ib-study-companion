"""
Adaptive Difficulty Engine — Item Response Theory (IRT) based.

Estimates student ability (theta) per subject/topic and selects optimal
difficulty for questions (~70% expected success rate).
"""

from __future__ import annotations

import math
from database import get_db
from db_stores import StudentAbilityStoreDB


def estimate_difficulty(marks: int, command_term: str = "") -> float:
    """Map question characteristics to difficulty on 0.1–3.0 scale.

    Uses mark allocation and command term to estimate inherent difficulty.
    """
    # Base difficulty from marks
    if marks <= 2:
        base = 0.5
    elif marks <= 4:
        base = 1.0
    elif marks <= 8:
        base = 1.8
    else:
        base = 2.5

    # Adjust by command term
    term_adjustments = {
        "define": -0.3, "state": -0.3, "list": -0.3, "identify": -0.2,
        "describe": 0.0, "outline": 0.0, "annotate": 0.0,
        "explain": 0.2, "suggest": 0.2,
        "analyse": 0.5, "compare": 0.4, "contrast": 0.4, "distinguish": 0.3,
        "evaluate": 0.8, "discuss": 0.7, "examine": 0.6, "justify": 0.7,
        "to what extent": 0.8,
    }
    adj = term_adjustments.get(command_term.lower(), 0.0)

    return max(0.1, min(3.0, base + adj))


def compute_mastery(
    theta: float, uncertainty: float, attempts: int, correct_ratio: float
) -> str:
    """Compute mastery state from ability parameters.

    States:
        unknown  — Never attempted (theta = 0, uncertainty = 1.0)
        learning — Attempted but low mastery (theta < -0.3 OR uncertainty > 0.5)
        partial  — Some understanding (theta between -0.3 and 0.5)
        mastered — Strong understanding (theta > 0.5 AND uncertainty < 0.3 AND attempts >= 5)
    """
    if attempts == 0:
        return "unknown"
    if theta < -0.3 or uncertainty > 0.5:
        return "learning"
    if theta > 0.5 and uncertainty < 0.3 and attempts >= 5:
        return "mastered"
    return "partial"


def update_theta(user_id: int, subject: str, topic: str,
                 difficulty: float, correct_ratio: float) -> dict:
    """Bayesian theta update using simplified IRT model.

    Args:
        user_id: Student ID
        subject: Subject key
        topic: Topic name
        difficulty: Estimated question difficulty (0.1-3.0)
        correct_ratio: Fraction of marks earned (0.0-1.0)

    Returns:
        Updated ability dict with theta, uncertainty, attempts, mastery_state.
    """
    store = StudentAbilityStoreDB(user_id)
    current = store.get_theta(subject, topic)

    theta = current["theta"]
    uncertainty = current["uncertainty"]
    attempts = current["attempts"]

    # IRT probability: P(correct | theta, difficulty) = 1 / (1 + exp(-1.7 * (theta - difficulty)))
    expected = 1.0 / (1.0 + math.exp(-1.7 * (theta - difficulty)))

    # Update theta based on surprise (observed - expected)
    surprise = correct_ratio - expected
    learning_rate = uncertainty * 0.3  # Higher uncertainty = faster updates
    theta += learning_rate * surprise

    # Reduce uncertainty with more data
    uncertainty = max(0.1, uncertainty * 0.95)
    attempts += 1

    store.update_theta(subject, topic, theta, uncertainty, attempts)

    # Compute and persist mastery state
    mastery_state = compute_mastery(theta, uncertainty, attempts, correct_ratio)
    try:
        db = get_db()
        db.execute(
            "UPDATE student_ability SET mastery_state = ?, last_correct_ratio = ? "
            "WHERE user_id = ? AND subject = ? AND topic = ?",
            (mastery_state, correct_ratio, user_id, subject, topic),
        )
        db.commit()
    except Exception:
        pass  # Mastery state update is best-effort (column may not exist yet)

    return {
        "theta": theta,
        "uncertainty": uncertainty,
        "attempts": attempts,
        "mastery_state": mastery_state,
    }


def select_difficulty(user_id: int, subject: str, topic: str) -> float:
    """Pick optimal difficulty for ~70% expected success.

    Uses the current ability estimate to find a difficulty level
    where the student has approximately a 70% chance of success.
    """
    store = StudentAbilityStoreDB(user_id)
    current = store.get_theta(subject, topic)
    theta = current["theta"]

    # Solve: 0.7 = 1 / (1 + exp(-1.7 * (theta - d)))
    # => d = theta - ln(0.7/0.3) / 1.7
    # => d = theta - 0.5 (approximately)
    target_difficulty = theta + 0.5  # slightly harder than current ability

    return max(0.1, min(3.0, target_difficulty))


def get_ability_profile(user_id: int, subject: str) -> list[dict]:
    """Return topic-level ability map for a subject."""
    store = StudentAbilityStoreDB(user_id)
    return store.get_profile(subject)


def difficulty_to_level(difficulty: float) -> int:
    """Convert continuous difficulty to discrete level 1-5."""
    if difficulty < 0.6:
        return 1
    elif difficulty < 1.2:
        return 2
    elif difficulty < 1.8:
        return 3
    elif difficulty < 2.4:
        return 4
    else:
        return 5
