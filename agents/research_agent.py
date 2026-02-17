"""Research Agent — Real-world examples using Gemini search grounding.

Finds real-world examples, case studies, and citations for EE/TOK/IA work.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

from agents.base import AgentResponse

load_dotenv()

RESEARCH_SYSTEM = """You are an IB research assistant helping students find real-world
examples and evidence for their coursework (Extended Essays, TOK essays, IAs).

When finding examples:
1. Provide REAL, verifiable examples with dates and sources
2. Explain why each example is relevant to the student's topic
3. Suggest how the student could use it in their work (e.g., as a TOK real-life situation,
   as an EE case study, as IA context)
4. Format citations in a way suitable for IB coursework

FORMAT each example as:
EXAMPLE [n]:
Title: [brief title]
Source: [publication/organization, year]
Summary: [2-3 sentences explaining the example]
Relevance: [how it connects to the student's topic]
IB Usage: [how to use it in their coursework]"""


class ResearchAgent:
    """Finds real-world examples using Gemini search grounding."""

    AGENT_NAME = "research_agent"

    def __init__(self) -> None:
        self._model = None
        google_key = os.getenv("GOOGLE_API_KEY")
        if google_key:
            try:
                import google.generativeai as genai

                genai.configure(api_key=google_key)
                self._model = genai.GenerativeModel("gemini-2.0-flash")
            except ImportError:
                pass

    def find_examples(
        self,
        topic: str,
        subject: str,
        count: int = 3,
        doc_type: str = "",
    ) -> AgentResponse:
        """Find real-world examples for a given topic."""
        if not self._model:
            return AgentResponse(
                content="Research requires a Google API key.",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

        context = ""
        if doc_type:
            doc_labels = {
                "ee": "Extended Essay",
                "ia": "Internal Assessment",
                "tok_essay": "TOK Essay",
                "tok_exhibition": "TOK Exhibition",
            }
            context = f"\nContext: The student is working on their {doc_labels.get(doc_type, 'coursework')}."

        prompt = f"""{RESEARCH_SYSTEM}

TASK: Find {count} real-world examples related to:
Topic: {topic}
Subject: {subject}
{context}

Search for recent, relevant, and verifiable examples that an IB student could cite.
Prioritize examples from the last 5 years when possible."""

        try:
            from ai_resilience import resilient_llm_call

            response_text, _ = resilient_llm_call("gemini", "gemini-2.0-flash", prompt)
            return AgentResponse(
                content=response_text,
                agent=self.AGENT_NAME,
                confidence=0.75,
                metadata={
                    "topic": topic,
                    "subject": subject,
                    "count": count,
                },
                follow_up="Would you like me to find more examples or focus on a specific aspect?",
            )
        except Exception as e:
            return AgentResponse(
                content=f"Research search failed: {e}",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )
