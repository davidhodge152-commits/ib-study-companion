"""
AI Tutor — Socratic teaching mode using Gemini.

Provides guided, interactive tutoring that adapts to the student's ability
and uses the Socratic method to deepen understanding.
"""

from __future__ import annotations

import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

TUTOR_SYSTEM_PROMPT = """You are an expert IB {subject} tutor with deep knowledge of the IB Diploma Programme.

YOUR TEACHING APPROACH:
1. Use the SOCRATIC METHOD — guide students through questions rather than giving direct answers
2. When a student asks "explain X", first check what they already know, then build on that
3. When helping with a question, break it down into steps and guide them through each one
4. Adapt your language complexity to the student's ability level
5. Reference IB mark scheme language and command term expectations when relevant
6. Use real-world examples to illustrate abstract concepts
7. Celebrate progress and correct mistakes gently

STUDENT CONTEXT:
- Subject: {subject}
- Topic: {topic}
- Ability level (theta): {theta} (scale: -2 to +2, where 0 is average)
{ability_note}

RULES:
- Keep responses concise (2-4 paragraphs max unless explaining something complex)
- Ask follow-up questions to check understanding
- If the student seems confused, simplify your explanation
- Reference specific IB syllabus content when possible
- Never be condescending — treat the student as a capable learner
- Use markdown formatting for clarity (bold key terms, bullet points for lists)"""


class TutorSession:
    """Manages a single tutoring conversation."""

    def __init__(self, subject: str, topic: str, ability_theta: float = 0.0):
        self.subject = subject
        self.topic = topic
        self.ability_theta = ability_theta

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise EnvironmentError("GOOGLE_API_KEY not set")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    def respond(self, messages: list[dict]) -> str:
        """Generate a tutor response given conversation history.

        Args:
            messages: List of dicts with 'role' and 'content' keys.

        Returns:
            Tutor response text.
        """
        # Build ability note
        if self.ability_theta > 1.0:
            ability_note = "This is an advanced student. Use sophisticated language and deeper analysis."
        elif self.ability_theta > 0.0:
            ability_note = "This student has solid foundations. Push them towards higher-order thinking."
        elif self.ability_theta > -1.0:
            ability_note = "This student is developing. Use clear, step-by-step explanations."
        else:
            ability_note = "This student needs extra support. Use simple language and concrete examples."

        system = TUTOR_SYSTEM_PROMPT.format(
            subject=self.subject,
            topic=self.topic,
            theta=f"{self.ability_theta:.1f}",
            ability_note=ability_note,
        )

        # Build conversation for Gemini
        conversation = [system + "\n\n"]
        for msg in messages:
            role = "Student" if msg["role"] == "user" else "Tutor"
            conversation.append(f"{role}: {msg['content']}")

        conversation.append("Tutor:")
        full_prompt = "\n\n".join(conversation)

        response = self.model.generate_content(full_prompt)
        return response.text
