"""Semantic Student Memory — persistent learning profile.

Remembers student's learning style, preferred analogies, recurring struggles,
and cross-curricular connections across sessions.

Memory types:
    learning_style — visual, auditory, kinesthetic preferences
    interest       — personal interests for analogies (e.g., "loves Formula 1")
    struggle       — recurring difficulty patterns (e.g., "forgets +C in integration")
    preference     — explanation preferences (e.g., "prefers step-by-step")
    context        — cross-curricular connections (e.g., "takes both Physics and Math AA")
"""

from __future__ import annotations

import os
from datetime import datetime

from database import get_db


MEMORY_TYPES = {"learning_style", "interest", "struggle", "preference", "context", "area_of_knowledge"}

EXTRACTION_PROMPT = """Analyze this tutoring conversation and extract learnable facts about the student.

Look for:
- Learning style preferences (visual, step-by-step, examples-first, etc.)
- Personal interests mentioned (hobbies, sports, passions — useful for analogies)
- Recurring struggles or mistakes
- Explanation preferences
- Cross-curricular connections (subjects they take, links they make)

Conversation:
{conversation}

Return ONLY a JSON array of objects with keys: type, key, value
Types: learning_style, interest, struggle, preference, context

Example:
[
  {{"type": "interest", "key": "hobby_f1", "value": "Student loves Formula 1 racing"}},
  {{"type": "struggle", "key": "integration_constant", "value": "Frequently forgets +C in integration"}}
]

If no learnable facts found, return: []"""


class StudentMemory:
    """Persistent semantic memory for a student."""

    def __init__(self, user_id: int) -> None:
        self.user_id = user_id

    def remember(
        self,
        memory_type: str,
        key: str,
        value: str,
        source: str = "",
        confidence: float = 1.0,
    ) -> None:
        """Store or update a memory."""
        if memory_type not in MEMORY_TYPES:
            return

        now = datetime.now().isoformat()
        db = get_db()
        db.execute(
            "INSERT INTO student_memory "
            "(user_id, memory_type, key, value, confidence, source, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, memory_type, key) DO UPDATE SET "
            "value = excluded.value, confidence = excluded.confidence, "
            "updated_at = excluded.updated_at",
            (self.user_id, memory_type, key, value, confidence, source, now, now),
        )
        db.commit()

    def recall(self, memory_type: str | None = None) -> list[dict]:
        """Recall memories, optionally filtered by type."""
        db = get_db()
        if memory_type:
            rows = db.execute(
                "SELECT memory_type, key, value, confidence, source, updated_at "
                "FROM student_memory WHERE user_id = ? AND memory_type = ? "
                "ORDER BY updated_at DESC",
                (self.user_id, memory_type),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT memory_type, key, value, confidence, source, updated_at "
                "FROM student_memory WHERE user_id = ? "
                "ORDER BY memory_type, updated_at DESC",
                (self.user_id,),
            ).fetchall()

        return [dict(r) for r in rows]

    def recall_for_prompt(self, subject: str = "") -> str:
        """Format memories for injection into agent system prompts.

        Returns a human-readable string like:
        'Student loves F1, prefers step-by-step explanations,
         frequently forgets to add +C in integration'
        """
        memories = self.recall()
        if not memories:
            return ""

        sections: dict[str, list[str]] = {
            "learning_style": [],
            "interest": [],
            "struggle": [],
            "preference": [],
            "context": [],
            "area_of_knowledge": [],
        }

        for m in memories:
            mt = m["memory_type"]
            if mt in sections:
                sections[mt].append(m["value"])

        parts: list[str] = []
        labels = {
            "interest": "Interests",
            "learning_style": "Learning style",
            "struggle": "Known struggles",
            "preference": "Preferences",
            "context": "Context",
            "area_of_knowledge": "Areas of Knowledge",
        }

        for key, label in labels.items():
            items = sections.get(key, [])
            if items:
                parts.append(f"- {label}: {'; '.join(items)}")

        if not parts:
            return ""

        return "STUDENT MEMORY:\n" + "\n".join(parts)

    def forget(self, memory_type: str, key: str) -> None:
        """Remove a specific memory."""
        db = get_db()
        db.execute(
            "DELETE FROM student_memory WHERE user_id = ? AND memory_type = ? AND key = ?",
            (self.user_id, memory_type, key),
        )
        db.commit()

    def auto_extract(self, conversation: list[dict]) -> list[dict]:
        """Use Gemini to extract learnable facts from a conversation.

        Returns list of extracted memories (also persists them).
        """
        if len(conversation) < 2:
            return []

        # Format conversation
        conv_text = "\n".join(
            f"{'Student' if m['role'] == 'user' else 'Tutor'}: {m['content']}"
            for m in conversation[-10:]  # Last 10 messages
        )

        google_key = os.getenv("GOOGLE_API_KEY")
        if not google_key:
            return []

        try:
            import google.generativeai as genai
            import json

            genai.configure(api_key=google_key)
            model = genai.GenerativeModel("gemini-2.0-flash")

            prompt = EXTRACTION_PROMPT.format(conversation=conv_text)
            response = model.generate_content(prompt)
            raw = response.text.strip()

            # Extract JSON from response (handle markdown code blocks)
            if "```" in raw:
                start = raw.index("[")
                end = raw.rindex("]") + 1
                raw = raw[start:end]

            extracted = json.loads(raw)
            if not isinstance(extracted, list):
                return []

            results: list[dict] = []
            for item in extracted:
                if not isinstance(item, dict):
                    continue
                mt = item.get("type", "")
                key = item.get("key", "")
                value = item.get("value", "")
                if mt in MEMORY_TYPES and key and value:
                    self.remember(mt, key, value, source="auto_extract", confidence=0.7)
                    results.append(item)

            return results
        except Exception:
            return []
