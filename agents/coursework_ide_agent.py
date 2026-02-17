"""Coursework IDE Agent — Process-oriented coursework support.

Helps students during the months of research and drafting (not just
post-mortem grading). Checks topic feasibility, analyzes data with
statistical tests, provides incremental draft feedback, and suggests
next steps based on milestone progress.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import TYPE_CHECKING

from dotenv import load_dotenv

from agents.base import AgentResponse

if TYPE_CHECKING:
    from rag_engine import RAGEngine

load_dotenv()

FEASIBILITY_SYSTEM = """You are an experienced IB coursework supervisor reviewing a topic proposal.

SUBJECT: {subject}
DOCUMENT TYPE: {doc_type_label}
{school_constraints}

Evaluate this topic proposal against:
1. IB criterion requirements — will this topic allow the student to access top marks?
2. Practical constraints — can this be completed within IB timelines?
3. Scope — is it too broad, too narrow, or well-scoped?
4. Originality — does it demonstrate personal engagement?
5. Ethical considerations — any ethical approval needed?

{rag_context}

FORMAT your response as:
FEASIBILITY_SCORE: [1-10]
VERDICT: [Excellent / Good / Needs Refinement / Not Recommended]

STRENGTHS:
- [strength 1]
- [strength 2]

CONCERNS:
- [concern 1]
- [concern 2]

SUGGESTIONS:
- [alternative/improvement 1]
- [alternative/improvement 2]

ALTERNATIVE_TOPICS:
1. [alternative topic suggestion with brief justification]
2. [alternative topic suggestion with brief justification]

NEXT_STEPS:
1. [immediate action item]
2. [second action item]
3. [third action item]"""

DATA_ANALYSIS_SYSTEM = """You are an IB science teacher helping a student analyze experimental data.

SUBJECT: {subject}
HYPOTHESIS: {hypothesis}

The student has provided raw data. Your tasks:
1. Identify appropriate statistical tests for this data
2. Write Python code to perform the analysis
3. Explain results in IB-appropriate language
4. Suggest evaluation points (systematic errors, improvements)

For IB science IAs, students need:
- Appropriate data processing (mean, std dev, uncertainties)
- Statistical tests (t-test, chi-squared, Pearson correlation as appropriate)
- Graphs with proper labels, units, error bars
- Clear statement of whether hypothesis is supported"""

DRAFT_REVIEW_SYSTEM = """You are an IB coursework moderator providing incremental feedback.

SUBJECT: {subject}
DOCUMENT TYPE: {doc_type_label}
CRITERION FOCUS: {criterion}
DRAFT VERSION: {version}

{previous_feedback_context}

REVIEW PROTOCOL:
1. Assess this draft against the specified criterion
2. If previous feedback exists, check which improvements were addressed
3. Identify NEW issues not mentioned in previous feedback
4. Estimate criterion score

FORMAT:
CRITERION_SCORE: [estimated] / [max]

RESOLVED (from previous feedback):
- [issue that was addressed] ✓

NEW_ISSUES:
- [new issue 1]
- [new issue 2]

PERSISTENT_ISSUES (still not addressed):
- [unresolved issue from previous feedback]

SPECIFIC_SUGGESTIONS:
- [actionable suggestion with example/reference]

PROGRESS: [improving / stagnant / declining]"""

DOC_TYPE_LABELS = {
    "ia": "Internal Assessment",
    "ee": "Extended Essay",
    "tok_essay": "TOK Essay",
    "tok_exhibition": "TOK Exhibition",
}


class CourseworkIDEAgent:
    """Process-oriented coursework support agent."""

    AGENT_NAME = "coursework_ide_agent"

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

    def check_feasibility(
        self,
        topic_proposal: str,
        subject: str,
        doc_type: str = "ia",
        school_constraints: str = "",
    ) -> AgentResponse:
        """Evaluate a coursework topic proposal for feasibility."""
        if self._provider == "none":
            return AgentResponse(
                content="Coursework IDE requires an API key (Anthropic or Google).",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

        doc_type_label = DOC_TYPE_LABELS.get(doc_type, "Coursework")

        # RAG context for past successful topics
        rag_context = ""
        if self.rag_engine:
            try:
                chunks = self.rag_engine.query(
                    query_text=f"{subject} {doc_type_label} criteria requirements",
                    n_results=3,
                    doc_type="subject_guide",
                )
                if chunks:
                    rag_context = (
                        "RELEVANT IB CRITERIA:\n"
                        + "\n---\n".join(c.text[:300] for c in chunks)
                    )
            except Exception:
                pass

        constraints_text = (
            f"SCHOOL CONSTRAINTS: {school_constraints}" if school_constraints else ""
        )

        system = FEASIBILITY_SYSTEM.format(
            subject=subject,
            doc_type_label=doc_type_label,
            school_constraints=constraints_text,
            rag_context=rag_context,
        )

        prompt = f"TOPIC PROPOSAL:\n{topic_proposal}"

        try:
            response_text = self._call_llm(prompt, system)
            feasibility = self._parse_feasibility(response_text)

            return AgentResponse(
                content=response_text,
                agent=self.AGENT_NAME,
                confidence=0.85,
                metadata={
                    "feasibility_score": feasibility.get("score", 0),
                    "verdict": feasibility.get("verdict", ""),
                    "doc_type": doc_type,
                    "subject": subject,
                },
                follow_up="Would you like me to help refine your topic or explore one of the alternatives?",
            )
        except Exception as e:
            return AgentResponse(
                content=f"Error checking feasibility: {e}",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

    def analyze_data(
        self,
        raw_data: str,
        subject: str,
        hypothesis: str = "",
        user_id: int | None = None,
        session_id: int | None = None,
    ) -> AgentResponse:
        """Analyze experimental data with statistical tests."""
        if self._provider == "none":
            return AgentResponse(
                content="Data analysis requires an API key.",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

        # Generate analysis code
        system = DATA_ANALYSIS_SYSTEM.format(
            subject=subject, hypothesis=hypothesis or "Not specified"
        )

        prompt = (
            f"Analyze this experimental data:\n\n{raw_data[:5000]}\n\n"
            "Write Python code to:\n"
            "1. Calculate descriptive statistics (mean, std dev, uncertainties)\n"
            "2. Perform appropriate statistical tests\n"
            "3. Print results clearly\n\n"
            "Then explain the results for an IB student."
        )

        try:
            response_text = self._call_llm(prompt, system)

            # Try to extract and run any code
            analysis_result = self._run_analysis_code(response_text)

            # Combine LLM explanation with computed results
            if analysis_result:
                full_response = (
                    f"## Data Analysis — {subject}\n\n"
                    f"### Computed Results\n```\n{analysis_result}\n```\n\n"
                    f"### Interpretation\n{response_text}"
                )
            else:
                full_response = f"## Data Analysis — {subject}\n\n{response_text}"

            # Save analysis
            if user_id and session_id:
                self._save_analysis(session_id, raw_data, full_response)

            return AgentResponse(
                content=full_response,
                agent=self.AGENT_NAME,
                confidence=0.8,
                metadata={
                    "subject": subject,
                    "hypothesis": hypothesis,
                    "has_computed_results": analysis_result is not None,
                },
                follow_up="Would you like me to help interpret these results for your evaluation section?",
            )
        except Exception as e:
            return AgentResponse(
                content=f"Error analyzing data: {e}",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

    def review_draft(
        self,
        text: str,
        doc_type: str,
        subject: str,
        criterion: str = "",
        previous_feedback: list | None = None,
        version: int = 1,
        user_id: int | None = None,
        session_id: int | None = None,
    ) -> AgentResponse:
        """Provide incremental feedback on a coursework draft."""
        if self._provider == "none":
            return AgentResponse(
                content="Draft review requires an API key.",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

        doc_type_label = DOC_TYPE_LABELS.get(doc_type, "Coursework")

        # Build previous feedback context
        prev_context = ""
        if previous_feedback:
            prev_context = (
                "PREVIOUS FEEDBACK (check if addressed):\n"
                + "\n".join(f"- {fb}" for fb in previous_feedback[-5:])
            )

        system = DRAFT_REVIEW_SYSTEM.format(
            subject=subject,
            doc_type_label=doc_type_label,
            criterion=criterion or "All criteria",
            version=version,
            previous_feedback_context=prev_context,
        )

        prompt = f"DRAFT TEXT (Version {version}):\n\n{text[:8000]}"

        try:
            response_text = self._call_llm(prompt, system)

            # Save draft and feedback
            if user_id and session_id:
                self._save_draft(session_id, version, text, response_text)

            word_count = len(text.split())

            return AgentResponse(
                content=response_text,
                agent=self.AGENT_NAME,
                confidence=0.85,
                metadata={
                    "doc_type": doc_type,
                    "subject": subject,
                    "version": version,
                    "word_count": word_count,
                    "has_previous_feedback": bool(previous_feedback),
                },
                follow_up=f"Your draft is {word_count} words. Would you like me to focus on a specific criterion?",
            )
        except Exception as e:
            return AgentResponse(
                content=f"Error reviewing draft: {e}",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

    def suggest_next_step(
        self, session_state: dict
    ) -> AgentResponse:
        """Suggest the next step based on coursework progress."""
        if self._provider == "none":
            return AgentResponse(
                content="Requires an API key.",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

        prompt = (
            "Based on this coursework session state, suggest the most impactful "
            "next step for the student:\n\n"
            f"{json.dumps(session_state, indent=2)}\n\n"
            "Consider:\n"
            "- What milestones have been completed?\n"
            "- What criterion scores are weakest?\n"
            "- What's the next deadline?\n\n"
            "Return a specific, actionable recommendation (2-3 sentences)."
        )

        try:
            response = self._call_llm(prompt)
            return AgentResponse(
                content=response,
                agent=self.AGENT_NAME,
                confidence=0.75,
                metadata={"action": "suggest_next_step"},
            )
        except Exception as e:
            return AgentResponse(
                content=f"Error: {e}",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

    def _call_llm(self, prompt: str, system: str = "") -> str:
        """Call the configured LLM provider."""
        if self._provider == "claude":
            kwargs = {
                "model": "claude-sonnet-4-5-20250929",
                "max_tokens": 2048,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                kwargs["system"] = system
            response = self._claude_client.messages.create(**kwargs)
            return response.content[0].text
        else:
            full_prompt = f"{system}\n\n{prompt}" if system else prompt
            return self._gemini_model.generate_content(full_prompt).text

    def _parse_feasibility(self, raw: str) -> dict:
        """Parse feasibility assessment response."""
        result = {"score": 0, "verdict": ""}
        for line in raw.splitlines():
            stripped = line.strip()
            if stripped.startswith("FEASIBILITY_SCORE:"):
                try:
                    result["score"] = int(stripped.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif stripped.startswith("VERDICT:"):
                result["verdict"] = stripped.split(":", 1)[1].strip()
        return result

    def _run_analysis_code(self, response_text: str) -> str | None:
        """Extract and run Python analysis code from LLM response."""
        try:
            from agents.stem_solver import STEMSolverAgent

            solver = STEMSolverAgent()

            # Extract code blocks
            if "```python" in response_text:
                start = response_text.index("```python") + len("```python")
                end = response_text.index("```", start)
                code = response_text[start:end].strip()
                return solver._execute_sandbox(code, timeout=10)
        except Exception:
            pass
        return None

    def _save_analysis(
        self, session_id: int, raw_data: str, result: str
    ) -> None:
        """Save data analysis to database."""
        try:
            from database import get_db

            db = get_db()
            db.execute(
                "INSERT INTO data_analyses "
                "(session_id, raw_data, analysis_result, created_at) "
                "VALUES (?, ?, ?, ?)",
                (session_id, raw_data[:10000], result, datetime.now().isoformat()),
            )
            db.commit()
        except Exception:
            pass

    def _save_draft(
        self, session_id: int, version: int, text: str, feedback: str
    ) -> None:
        """Save a draft with its feedback to the database."""
        try:
            from database import get_db

            db = get_db()
            db.execute(
                "INSERT INTO coursework_drafts "
                "(session_id, version, text_content, word_count, feedback, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    session_id,
                    version,
                    text[:50000],
                    len(text.split()),
                    json.dumps([feedback]),
                    datetime.now().isoformat(),
                ),
            )
            db.commit()
        except Exception:
            pass
