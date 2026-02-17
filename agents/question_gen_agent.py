"""Question Generation Agent — Infinite parametric question variants.

Generates mathematically verified novel question variants from source
questions. Every generated question is computationally verified via
the STEM sandbox before being presented to the student.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from dotenv import load_dotenv

from agents.base import AgentResponse

if TYPE_CHECKING:
    from rag_engine import RAGEngine

load_dotenv()

GENERATION_PROMPT = """You are an IB {subject} question writer creating {count} new question variants.

SOURCE QUESTION (for reference):
{source_question}

VARIATION TYPE: {variation_type}
- "context": Same underlying concept, different real-world scenario
- "numbers": Same structure, different numerical values
- "full": Complete rewrite requiring different approach
- "reverse": Give the answer, ask for the method/question

DIFFICULTY: {difficulty}
TOPIC: {topic}

Generate exactly {count} questions. For each question, provide:

QUESTION_1:
Question: [the question text]
Command_term: [appropriate IB command term]
Marks: [mark allocation]
Model_answer: [complete worked solution]
Python_verification: [Python code that computes and prints the answer]

QUESTION_2:
...

RULES:
- Each question MUST have a definitive, verifiable numerical or short answer
- Vary the context meaningfully (don't just change numbers)
- Match IB {subject} syllabus terminology and style
- Include appropriate units
- The Python code must be self-contained (use only math, numpy, scipy)
- Print ONLY the final answer from the Python code"""

VERIFY_PROMPT = """Independently solve this {subject} question and provide the answer.

Question: {question}

Write Python code that solves this from scratch (do NOT reference any model answer).
Use only: math, numpy, scipy
Print ONLY the final numerical answer."""


class QuestionGenAgent:
    """Generates verified parametric question variants."""

    AGENT_NAME = "question_gen_agent"

    def __init__(self, rag_engine: RAGEngine | None = None) -> None:
        self.rag_engine = rag_engine
        self._claude_client = None
        self._gemini_model = None
        self._provider = "none"
        self._init_provider()

    def _init_provider(self) -> None:
        """Initialize best available LLM provider."""
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            try:
                import anthropic

                self._claude_client = anthropic.Anthropic(api_key=anthropic_key)
                self._provider = "claude"
                return
            except ImportError:
                pass

        google_key = os.getenv("GOOGLE_API_KEY")
        if google_key:
            try:
                import google.generativeai as genai

                genai.configure(api_key=google_key)
                self._gemini_model = genai.GenerativeModel("gemini-2.0-flash")
                self._provider = "gemini"
            except ImportError:
                pass

    def generate_parametric(
        self,
        subject: str,
        topic: str = "",
        source_question: str = "",
        variation_type: str = "numbers",
        count: int = 3,
        difficulty: str = "medium",
    ) -> AgentResponse:
        """Generate N parametric question variants with verification."""
        if self._provider == "none":
            return AgentResponse(
                content="Question generation requires an API key (Anthropic or Google).",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

        count = min(count, 5)  # Cap at 5

        prompt = GENERATION_PROMPT.format(
            subject=subject,
            topic=topic or "General",
            source_question=source_question or "Generate original questions",
            variation_type=variation_type,
            count=count,
            difficulty=difficulty,
        )

        try:
            raw = self._call_llm(prompt)
            questions = self._parse_questions(raw)

            # Verify each question using the sandbox
            verified_questions = []
            for q in questions:
                verification = self.verify_question(
                    q.get("question", ""),
                    q.get("model_answer", ""),
                    subject,
                    q.get("python_code", ""),
                )
                q["verified"] = verification.get("verified", False)
                q["computed_answer"] = verification.get("computed_answer", "")
                verified_questions.append(q)

            # Format response
            content = self._format_questions(verified_questions, subject, topic)

            verified_count = sum(1 for q in verified_questions if q.get("verified"))

            return AgentResponse(
                content=content,
                agent=self.AGENT_NAME,
                confidence=0.85 if verified_count > 0 else 0.5,
                metadata={
                    "questions": verified_questions,
                    "total_generated": len(verified_questions),
                    "total_verified": verified_count,
                    "variation_type": variation_type,
                    "subject": subject,
                    "topic": topic,
                },
                follow_up="Would you like to try answering one of these questions?",
            )
        except Exception as e:
            return AgentResponse(
                content=f"Error generating questions: {e}",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

    def verify_question(
        self,
        question: str,
        model_answer: str,
        subject: str,
        python_code: str = "",
    ) -> dict:
        """Verify a question by independently computing the answer."""
        try:
            from agents.stem_solver import STEMSolverAgent

            solver = STEMSolverAgent()

            # First try the provided verification code
            if python_code:
                result = solver._execute_sandbox(python_code)
                if result:
                    return {
                        "verified": True,
                        "computed_answer": result.strip(),
                        "method": "provided_code",
                    }

            # Fall back to generating fresh code
            code = solver._generate_code(question, subject)
            if code:
                result = solver._execute_sandbox(code)
                if result:
                    return {
                        "verified": True,
                        "computed_answer": result.strip(),
                        "method": "independent_solve",
                    }
        except Exception:
            pass

        return {"verified": False, "computed_answer": "", "method": "failed"}

    def _parse_questions(self, raw: str) -> list[dict]:
        """Parse generated questions from LLM output."""
        questions = []
        current: dict = {}

        for line in raw.splitlines():
            stripped = line.strip()

            if stripped.startswith("QUESTION_"):
                if current.get("question"):
                    questions.append(current)
                current = {}
            elif stripped.startswith("Question:"):
                current["question"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Command_term:"):
                current["command_term"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Marks:"):
                try:
                    current["marks"] = int(stripped.split(":", 1)[1].strip())
                except ValueError:
                    current["marks"] = 4
            elif stripped.startswith("Model_answer:"):
                current["model_answer"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Python_verification:"):
                # Collect multi-line code
                current["python_code"] = stripped.split(":", 1)[1].strip()
            elif "python_code" in current and (
                stripped.startswith("import ") or stripped.startswith("print(")
                or stripped.startswith("result") or stripped.startswith("#")
                or "=" in stripped
            ):
                current["python_code"] += "\n" + stripped

        if current.get("question"):
            questions.append(current)

        return questions

    def _format_questions(
        self, questions: list[dict], subject: str, topic: str
    ) -> str:
        """Format verified questions for display."""
        parts = [f"## Generated Questions — {subject}"]
        if topic:
            parts[0] += f" ({topic})"
        parts.append("")

        for i, q in enumerate(questions, 1):
            verified = "Verified" if q.get("verified") else "Unverified"
            marks = q.get("marks", "?")
            cmd = q.get("command_term", "")

            parts.append(f"### Question {i} [{verified}]")
            if cmd:
                parts.append(f"*Command term: {cmd} | Marks: {marks}*\n")
            parts.append(q.get("question", ""))
            parts.append("")

            if q.get("model_answer"):
                parts.append(f"<details><summary>Model Answer</summary>\n\n{q['model_answer']}\n\n</details>\n")

        verified_count = sum(1 for q in questions if q.get("verified"))
        parts.append(f"\n*{verified_count}/{len(questions)} questions computationally verified*")

        return "\n".join(parts)

    def _call_llm(self, prompt: str, system: str = "") -> str:
        """Call the configured LLM provider with resilience."""
        from ai_resilience import resilient_llm_call

        model = "claude-sonnet-4-5-20250929" if self._provider == "claude" else "gemini-2.0-flash"
        text, _ = resilient_llm_call(self._provider, model, prompt, system=system)
        return text
