"""Grading Agent — IB Examiner using Gemini 2.0 Flash.

Enhanced version of IBGrader that integrates with the orchestrator,
injects examiner report warnings from RAG, and returns structured AgentResponse.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

try:
    import google.generativeai as genai
except ImportError:
    genai = None
from dotenv import load_dotenv

from agents.base import AgentResponse
from subject_config import get_subject_config

if TYPE_CHECKING:
    from rag_engine import RAGEngine

load_dotenv()

IB_EXAMINER_SYSTEM = """You are a SENIOR IB EXAMINER with 15+ years of experience marking
IB Diploma Programme papers. You are precise, fair, but strict.

YOUR GRADING PROTOCOL:

1. IDENTIFY the command term and apply expectations:
   - "Define"/"State"/"List" → factual recall, 1-2 marks
   - "Describe"/"Outline" → characteristics + detail, 2-4 marks
   - "Explain" → cause/mechanism with reasoning, 3-6 marks
   - "Analyse" → break down components, show relationships, 6-8 marks
   - "Evaluate"/"Discuss"/"To what extent" → balanced argument with judgement, 8-15 marks

2. APPLY mark scheme criteria. For each mark point earned, state which
   criterion it satisfies. For each missed, explain EXACTLY what was required.

3. CHECK for common IB penalties:
   - Vague language → deduct for lack of specificity
   - Missing key terminology → note which terms were expected
   - One-sided evaluation → cap at 50% for evaluative Qs
   - No real-world examples when expected → note the omission

4. ASSIGN a final mark and convert to a 1-7 grade.

5. PROVIDE structured feedback: STRENGTHS, IMPROVEMENTS, EXAMINER TIP.

FORMAT your response EXACTLY as:
MARK: [earned]/[total]
GRADE: [1-7]
PERCENTAGE: [integer]%

STRENGTHS:
- [point 1]
- [point 2]

IMPROVEMENTS:
- [point 1 with rubric reference]
- [point 2 with rubric reference]

EXAMINER_TIP:
[one specific, actionable tip]

FULL_COMMENTARY:
[2-3 sentences of overall assessment]

MODEL_ANSWER:
[concise model answer that would earn full marks]"""


class GradingAgent:
    """Grades student answers using Gemini with examiner report augmentation."""

    AGENT_NAME = "grading_agent"

    def __init__(self, rag_engine: RAGEngine | None = None) -> None:
        self.rag_engine = rag_engine
        self.model = None
        if genai is not None:
            api_key = os.getenv("GOOGLE_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel("gemini-2.0-flash")

    def grade(
        self,
        question: str,
        answer: str,
        subject: str,
        marks: int,
        command_term: str = "",
        subject_display: str = "",
        user_id: int | None = None,
    ) -> AgentResponse:
        """Grade a student answer and return AgentResponse."""
        if not self.model:
            return AgentResponse(
                content="Grading requires a Google API key.",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

        # Retrieve mark scheme + examiner warning context from RAG
        context_marks = "No mark scheme available — use general IB marking criteria."
        context_guide = ""
        examiner_warnings = ""

        if self.rag_engine:
            try:
                mark_chunks = self.rag_engine.query(
                    query_text=f"{subject} {command_term} mark scheme {question[:100]}",
                    n_results=5,
                    doc_type="mark_scheme",
                )
                context_marks = "\n---\n".join(c.text for c in mark_chunks) or context_marks
            except Exception:
                pass

            try:
                guide_chunks = self.rag_engine.query(
                    query_text=f"{subject} syllabus {question[:80]}",
                    n_results=3,
                    doc_type="subject_guide",
                )
                context_guide = "\n---\n".join(c.text for c in guide_chunks) or ""
            except Exception:
                pass

            # Examiner report warnings (Phase 2 enhancement)
            try:
                warnings = self.rag_engine.get_examiner_warnings(
                    subject=subject,
                    topic=subject_display or subject,
                )
                if warnings:
                    examiner_warnings = (
                        "\nEXAMINER REPORTS SAY:\n"
                        + "\n".join(f"- {w}" for w in warnings)
                    )
            except (AttributeError, Exception):
                pass

            # Mark scheme criteria (Phase 2 enhancement)
            try:
                criteria = self.rag_engine.get_mark_scheme_criteria(
                    subject=subject,
                    question_type=command_term,
                    marks=marks,
                )
                if criteria:
                    examiner_warnings += (
                        "\nMARK SCHEME CRITERIA:\n"
                        + "\n".join(f"- {c}" for c in criteria)
                    )
            except (AttributeError, Exception):
                pass

        # Build subject-specific context
        subject_context = ""
        config = get_subject_config(subject_display or subject.replace("_", " ").title())
        if config:
            ct_note = ""
            if command_term and command_term in config.key_command_terms:
                ct_note = f"\nCOMMAND TERM NOTE: {config.key_command_terms[command_term]}"

            pitfalls = "\n".join(f"  - {p}" for p in config.common_pitfalls)
            subject_context = f"""
SUBJECT-SPECIFIC INTELLIGENCE:
Category: {config.category}
{ct_note}

COMMON PITFALLS:
{pitfalls}
"""

        prompt = f"""MARK SCHEME CONTEXT:
{context_marks}

SYLLABUS CONTEXT:
{context_guide}
{subject_context}{examiner_warnings}

QUESTION ({marks} marks):
{question}

COMMAND TERM: {command_term or 'Not specified'}

STUDENT ANSWER:
{answer}

Grade this answer according to your protocol. The question is worth {marks} marks."""

        from ai_resilience import resilient_llm_call

        raw, _ = resilient_llm_call(
            "gemini", "gemini-2.0-flash", prompt, system=IB_EXAMINER_SYSTEM,
        )

        # Parse structured response
        parsed = self._parse(raw, marks)

        # Validate parsed output
        valid, warnings = self._validate_parse(parsed, marks)
        if not valid:
            # Retry once with format reminder
            retry_prompt = (
                prompt + "\n\nIMPORTANT FORMAT REMINDER: mark_earned must be <= "
                f"{marks}, grade must be 1-7, percentage must be 0-100, "
                "and you must provide at least some strengths or improvements."
            )
            try:
                raw, _ = resilient_llm_call(
                    "gemini", "gemini-2.0-flash", retry_prompt,
                    system=IB_EXAMINER_SYSTEM,
                )
                parsed = self._parse(raw, marks)
                valid, warnings = self._validate_parse(parsed, marks)
            except Exception:
                pass

        # Update adaptive theta
        if user_id:
            try:
                from adaptive import estimate_difficulty, update_theta

                diff = estimate_difficulty(marks, command_term)
                correct_ratio = (
                    parsed["mark_earned"] / parsed["mark_total"]
                    if parsed["mark_total"] > 0
                    else 0
                )
                update_theta(
                    user_id, subject, subject_display or subject, diff, correct_ratio
                )
            except Exception:
                pass

        return AgentResponse(
            content=raw,
            agent=self.AGENT_NAME,
            confidence=0.85,
            metadata=parsed,
            follow_up="Would you like me to explain any of the mark scheme criteria?",
            validated=valid,
            validation_warnings=warnings,
        )

    def _parse(self, raw: str, total_marks: int) -> dict:
        """Parse Gemini grading output into structured dict."""
        mark_earned = 0
        grade = 4
        percentage = 50
        strengths: list[str] = []
        improvements: list[str] = []
        examiner_tip = ""
        full_commentary = ""
        model_answer = ""

        section = ""
        for line in raw.splitlines():
            stripped = line.strip()

            if stripped.startswith("MARK:"):
                parts = stripped.split(":")[1].strip().split("/")
                try:
                    mark_earned = int(parts[0].strip())
                except (ValueError, IndexError):
                    pass
            elif stripped.startswith("GRADE:"):
                try:
                    grade = int(stripped.split(":")[1].strip()[0])
                    grade = max(1, min(7, grade))
                except (ValueError, IndexError):
                    pass
            elif stripped.startswith("PERCENTAGE:"):
                try:
                    percentage = int(
                        "".join(c for c in stripped.split(":")[1] if c.isdigit())
                    )
                except (ValueError, IndexError):
                    pass
            elif stripped.startswith("STRENGTHS:"):
                section = "strengths"
            elif stripped.startswith("IMPROVEMENTS:"):
                section = "improvements"
            elif stripped.startswith("EXAMINER_TIP:"):
                section = "tip"
            elif stripped.startswith("FULL_COMMENTARY:"):
                section = "commentary"
            elif stripped.startswith("MODEL_ANSWER:"):
                section = "model_answer"
                first = stripped.split(":", 1)[1].strip()
                if first:
                    model_answer += first + "\n"
            elif stripped.startswith("- ") and section == "strengths":
                strengths.append(stripped[2:])
            elif stripped.startswith("- ") and section == "improvements":
                improvements.append(stripped[2:])
            elif section == "tip" and stripped:
                examiner_tip += stripped + " "
            elif section == "commentary" and stripped:
                full_commentary += stripped + " "
            elif section == "model_answer" and stripped:
                model_answer += stripped + "\n"

        return {
            "mark_earned": mark_earned,
            "mark_total": total_marks,
            "grade": grade,
            "percentage": percentage,
            "strengths": strengths,
            "improvements": improvements,
            "examiner_tip": examiner_tip.strip(),
            "full_commentary": full_commentary.strip(),
            "model_answer": model_answer.strip(),
        }

    @staticmethod
    def _validate_parse(parsed: dict, marks: int) -> tuple[bool, list[str]]:
        """Validate parsed grading output. Returns (is_valid, warnings)."""
        warnings: list[str] = []

        if parsed["mark_earned"] > marks:
            warnings.append(f"mark_earned ({parsed['mark_earned']}) > mark_total ({marks})")
        if not 1 <= parsed["grade"] <= 7:
            warnings.append(f"grade ({parsed['grade']}) outside 1-7 range")
        if not 0 <= parsed["percentage"] <= 100:
            warnings.append(f"percentage ({parsed['percentage']}) outside 0-100 range")
        if not parsed["strengths"] and not parsed["improvements"]:
            warnings.append("no strengths or improvements provided")

        return (len(warnings) == 0, warnings)
