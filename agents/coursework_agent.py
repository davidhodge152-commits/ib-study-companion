"""Coursework Agent — IA/EE/TOK review using Claude (with Gemini fallback).

Provides criterion-by-criterion feedback on Internal Assessments,
Extended Essays, and TOK essays/exhibitions.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from dotenv import load_dotenv

from agents.base import AgentResponse
from subject_config import get_subject_config

if TYPE_CHECKING:
    from rag_engine import RAGEngine

load_dotenv()

COURSEWORK_SYSTEM = """You are a Senior IB {doc_type_label} Moderator with extensive experience
reviewing student coursework across all IB subjects.

DOCUMENT TYPE: {doc_type_label}
SUBJECT: {subject}
{criterion_context}

YOUR REVIEW PROTOCOL:
1. Assess the work against EACH relevant criterion from the IB rubric
2. For each criterion:
   - State the criterion name and max marks
   - Identify what the student did well (with quotes/references)
   - Identify gaps or weaknesses (with specific suggestions)
   - Estimate a mark range (e.g., "4-5 out of 6")
3. Provide an overall assessment with:
   - Total estimated mark range
   - Top 3 actionable improvements ranked by impact
   - One strength to maintain

FORMAT your response as:
OVERALL: [estimated mark range] / [total]

CRITERION A: [name] ([marks range] / [max])
Strengths: [specific points]
Improvements: [specific suggestions]

CRITERION B: [name] ([marks range] / [max])
...

TOP IMPROVEMENTS:
1. [highest impact change]
2. [second highest]
3. [third highest]

KEY STRENGTH:
[what to maintain]"""

DOC_TYPE_LABELS = {
    "ia": "Internal Assessment",
    "ee": "Extended Essay",
    "tok_essay": "TOK Essay",
    "tok_exhibition": "TOK Exhibition",
}

# IB assessment criteria by document type
CRITERIA = {
    "ia": {
        "science": [
            "A: Personal Engagement (2)",
            "B: Exploration (6)",
            "C: Analysis (6)",
            "D: Evaluation (6)",
            "E: Communication (4)",
        ],
        "default": [
            "A: Knowledge and Understanding",
            "B: Application and Analysis",
            "C: Synthesis and Evaluation",
            "D: Communication",
        ],
    },
    "ee": [
        "A: Focus and Method (6)",
        "B: Knowledge and Understanding (6)",
        "C: Critical Thinking (12)",
        "D: Presentation (4)",
        "E: Engagement (6)",
    ],
    "tok_essay": [
        "Understanding knowledge questions",
        "Quality of analysis of knowledge questions",
        "Examples and their effectiveness",
        "Quality of argument and counter-argument",
    ],
    "tok_exhibition": [
        "Links between objects and IA prompt",
        "Justification of links to TOK",
        "Coherence and clarity of commentary",
    ],
}


class CourseworkAgent:
    """Reviews IA/EE/TOK work using Claude with Gemini fallback."""

    AGENT_NAME = "coursework_agent"

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

    def review(
        self,
        text: str,
        doc_type: str,
        subject: str,
        criterion: str = "",
    ) -> AgentResponse:
        """Review coursework and provide criterion-by-criterion feedback."""
        if self._provider == "none":
            return AgentResponse(
                content="Coursework review requires an API key (Anthropic or Google).",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

        doc_type_label = DOC_TYPE_LABELS.get(doc_type, "Coursework")

        # Build criterion context
        criterion_context = self._get_criteria_context(doc_type, subject)

        # Retrieve rubric from RAG if available
        rag_context = ""
        if self.rag_engine:
            try:
                chunks = self.rag_engine.query(
                    query_text=f"{subject} {doc_type_label} assessment criteria rubric",
                    n_results=4,
                    doc_type="subject_guide",
                )
                if chunks:
                    rag_context = (
                        "\nRELEVANT RUBRIC CONTEXT:\n"
                        + "\n---\n".join(c.text[:300] for c in chunks)
                    )
            except Exception:
                pass

        system = COURSEWORK_SYSTEM.format(
            doc_type_label=doc_type_label,
            subject=subject,
            criterion_context=criterion_context + rag_context,
        )

        # Focus on specific criterion if requested
        focus_note = ""
        if criterion:
            focus_note = f"\n\nFOCUS: The student specifically wants feedback on criterion: {criterion}\n"

        prompt = f"""STUDENT'S {doc_type_label.upper()} ({subject}):

{text[:8000]}
{focus_note}
Review this work according to your protocol."""

        try:
            if self._provider == "claude":
                response = self._claude_client.messages.create(
                    model="claude-sonnet-4-5-20250929",
                    max_tokens=2048,
                    system=system,
                    messages=[{"role": "user", "content": prompt}],
                )
                response_text = response.content[0].text
            else:
                response_text = self._gemini_model.generate_content(
                    f"{system}\n\n{prompt}"
                ).text

            return AgentResponse(
                content=response_text,
                agent=self.AGENT_NAME,
                confidence=0.85,
                metadata={
                    "doc_type": doc_type,
                    "subject": subject,
                    "provider": self._provider,
                },
                follow_up="Would you like me to focus on a specific criterion in more detail?",
            )
        except Exception as e:
            return AgentResponse(
                content=f"Error reviewing coursework: {e}",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

    def _get_criteria_context(self, doc_type: str, subject: str) -> str:
        """Build criterion context string for the system prompt."""
        if doc_type == "ia":
            config = get_subject_config(subject)
            category = config.category if config else "default"
            criteria_list = CRITERIA["ia"].get(
                category if category == "science" else "default",
                CRITERIA["ia"]["default"],
            )
        elif doc_type in CRITERIA:
            criteria_list = CRITERIA[doc_type]
        else:
            criteria_list = ["General assessment criteria"]

        return (
            "\nASSESSMENT CRITERIA:\n"
            + "\n".join(f"- {c}" for c in criteria_list)
        )
