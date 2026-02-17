"""Tutor Agent — Socratic teaching using Claude (with Gemini fallback).

Uses Claude Sonnet for superior Socratic reasoning, adapts to student ability,
references past misconceptions, and enforces guided discovery over direct answers.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from dotenv import load_dotenv

from agents.base import AgentResponse

if TYPE_CHECKING:
    from rag_engine import RAGEngine

load_dotenv()

TUTOR_SYSTEM = """You are an expert IB {subject} tutor with deep knowledge of the IB Diploma Programme.

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

{syllabus_context}

{memory_context}

{misconception_context}

RULES:
- Keep responses concise (2-4 paragraphs max unless explaining something complex)
- If the student asks for the answer directly, guide them towards it with questions instead
- Ask follow-up questions to check understanding
- If the student seems confused, simplify your explanation
- Reference specific IB syllabus content when possible
- Never be condescending — treat the student as a capable learner
- Use markdown formatting for clarity (bold key terms, bullet points for lists)"""


def _ability_note(theta: float) -> str:
    if theta > 1.0:
        return "This is an advanced student. Use sophisticated language and deeper analysis."
    if theta > 0.0:
        return "This student has solid foundations. Push them towards higher-order thinking."
    if theta > -1.0:
        return "This student is developing. Use clear, step-by-step explanations."
    return "This student needs extra support. Use simple language and concrete examples."


class TutorAgent:
    """Socratic tutor using Claude with Gemini fallback."""

    AGENT_NAME = "tutor_agent"

    def __init__(self, rag_engine: RAGEngine | None = None) -> None:
        self.rag_engine = rag_engine
        self._claude_client = None
        self._gemini_model = None
        self._provider = "none"
        self._init_provider()

    def _init_provider(self) -> None:
        """Initialize best available LLM provider."""
        # Try Claude first (preferred for tutoring)
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            try:
                import anthropic

                self._claude_client = anthropic.Anthropic(api_key=anthropic_key)
                self._provider = "claude"
                return
            except ImportError:
                pass

        # Fall back to Gemini
        google_key = os.getenv("GOOGLE_API_KEY")
        if google_key:
            try:
                import google.generativeai as genai

                genai.configure(api_key=google_key)
                self._gemini_model = genai.GenerativeModel("gemini-2.0-flash")
                self._provider = "gemini"
            except ImportError:
                pass

    def tutor(
        self,
        messages: list[dict],
        subject: str,
        topic: str,
        ability_theta: float = 0.0,
        memory_context: str = "",
        misconceptions: list[str] | None = None,
    ) -> AgentResponse:
        """Generate a Socratic tutor response."""
        # Retrieve syllabus context from RAG
        syllabus_context = ""
        if self.rag_engine:
            try:
                chunks = self.rag_engine.query(
                    query_text=f"{subject} {topic} syllabus content",
                    n_results=3,
                    doc_type="subject_guide",
                )
                if chunks:
                    syllabus_context = (
                        "RELEVANT SYLLABUS CONTENT:\n"
                        + "\n".join(f"- {c.text[:200]}" for c in chunks)
                    )
            except Exception:
                pass

        # Build misconception context
        misconception_context = ""
        if misconceptions:
            misconception_context = (
                "STUDENT'S KNOWN MISCONCEPTIONS (address if relevant):\n"
                + "\n".join(f"- {m}" for m in misconceptions)
            )

        system = TUTOR_SYSTEM.format(
            subject=subject,
            topic=topic,
            theta=f"{ability_theta:.1f}",
            ability_note=_ability_note(ability_theta),
            syllabus_context=syllabus_context,
            memory_context=memory_context,
            misconception_context=misconception_context,
        )

        if self._provider not in ("claude", "gemini"):
            return AgentResponse(
                content="The AI tutor requires an API key (Anthropic or Google).",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

        response_text = self._call_llm(system, messages)

        return AgentResponse(
            content=response_text,
            agent=self.AGENT_NAME,
            confidence=0.9 if self._provider == "claude" else 0.8,
            metadata={"provider": self._provider},
        )

    def _call_llm(self, system: str, messages: list[dict]) -> str:
        """Call the configured LLM provider with resilience."""
        from ai_resilience import resilient_llm_call

        if self._provider == "claude":
            claude_messages = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "assistant"
                claude_messages.append({"role": role, "content": msg["content"]})
            text, _ = resilient_llm_call(
                "claude", "claude-sonnet-4-5-20250929", "",
                system=system, messages=claude_messages,
            )
            return text
        else:
            conversation = [system + "\n\n"]
            for msg in messages:
                role = "Student" if msg["role"] == "user" else "Tutor"
                conversation.append(f"{role}: {msg['content']}")
            conversation.append("Tutor:")
            prompt = "\n\n".join(conversation)
            text, _ = resilient_llm_call("gemini", "gemini-2.0-flash", prompt)
            return text
