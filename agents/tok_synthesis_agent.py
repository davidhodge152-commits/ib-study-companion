"""TOK Synthesis Agent — Cross-curricular Theory of Knowledge support.

Bridges student's subjects to help with TOK essays and exhibitions by
identifying connections between Areas of Knowledge (AoK) and Ways
of Knowing (WoK). Leverages student memory and knowledge graph to
provide personalized, cross-disciplinary synthesis.
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

TOK_SYSTEM = """You are an expert IB Theory of Knowledge teacher helping a student
connect their IB subjects to TOK concepts.

YOUR APPROACH:
1. Identify the relevant Areas of Knowledge (AoK) from the student's subjects
2. Map to Ways of Knowing (WoK): reason, language, sense perception, emotion,
   imagination, faith, intuition, memory
3. Find genuine philosophical connections between disciplines
4. Use concrete examples from the student's own subjects
5. Guide toward strong TOK arguments, not generic observations

STUDENT'S SUBJECTS: {subjects}
STUDENT CONTEXT: {memory_context}

KEY TOK CONCEPTS:
- Knowledge vs opinion, justified true belief
- Shared knowledge vs personal knowledge
- Knowledge frameworks: scope, applications, methodology, historical development
- Areas of Knowledge: Natural Sciences, Human Sciences, Mathematics, History,
  The Arts, Ethics, Religious Knowledge Systems, Indigenous Knowledge Systems

RULES:
- Always ground claims in specific subject examples
- Show how the SAME concept appears differently across disciplines
- Use the student's actual studied topics when possible
- Push beyond surface-level connections to genuine epistemological insights"""

SYNTHESIS_PROMPT = """Help this IB student with a TOK task.

STUDENT MESSAGE: {message}
{tok_prompt_context}

SUBJECTS AND RECENT TOPICS:
{subject_topics}

Provide a thoughtful, cross-curricular response that:
1. Identifies at least 2 relevant Areas of Knowledge
2. Explains how each AoK approaches the question differently
3. Uses specific examples from the student's subjects
4. Suggests Ways of Knowing that are relevant
5. Offers a nuanced perspective suitable for a TOK essay"""

CONNECTION_PROMPT = """Find deep TOK connections between these two subjects/topics:

SUBJECT 1: {subject1} — Topic: {topic1}
SUBJECT 2: {subject2} — Topic: {topic2}

For each connection:
1. Identify the shared epistemological question
2. Show how each discipline answers it differently
3. Map to TOK terminology (AoK, WoK, knowledge claims)
4. Provide a concrete example from each subject
5. Suggest how this could be used in a TOK essay

Return 2-3 deep connections, not surface-level observations."""


class TOKSynthesisAgent:
    """Cross-curricular Theory of Knowledge synthesis agent."""

    AGENT_NAME = "tok_synthesis_agent"

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

    def synthesize(
        self,
        message: str,
        student_subjects: list[dict] | None = None,
        student_memories: list[dict] | None = None,
        tok_prompt: str = "",
        user_id: int | None = None,
    ) -> AgentResponse:
        """Generate cross-curricular TOK synthesis."""
        if self._provider == "none":
            return AgentResponse(
                content="TOK synthesis agent requires an API key (Anthropic or Google).",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

        # Build subject context
        subjects = student_subjects or []
        subjects_str = ", ".join(
            f"{s.get('name', '')} {s.get('level', '')}" for s in subjects
        ) or "General IB"

        # Get memory context
        memory_context = ""
        if user_id:
            try:
                from memory import StudentMemory
                mem = StudentMemory(user_id)
                memory_context = mem.recall_for_prompt()
            except Exception:
                pass

        # Build subject-topic details with AoK mappings
        subject_topics = self._build_subject_topics(subjects, user_id)

        tok_prompt_context = f"TOK PRESCRIBED TITLE/PROMPT: {tok_prompt}" if tok_prompt else ""

        system = TOK_SYSTEM.format(
            subjects=subjects_str,
            memory_context=memory_context or "No memory available",
        )

        prompt = SYNTHESIS_PROMPT.format(
            message=message,
            tok_prompt_context=tok_prompt_context,
            subject_topics=subject_topics,
        )

        try:
            response_text = self._call_llm(prompt, system)

            # Store AoK memories for future use
            if user_id:
                self._store_aok_memories(user_id, subjects)

            return AgentResponse(
                content=response_text,
                agent=self.AGENT_NAME,
                confidence=0.85,
                metadata={
                    "subjects_used": [s.get("name", "") for s in subjects],
                    "tok_prompt": tok_prompt,
                },
                follow_up="Would you like me to find specific connections between two of your subjects?",
            )
        except Exception as e:
            return AgentResponse(
                content=f"Error in TOK synthesis: {e}",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

    def suggest_connections(
        self,
        subject1: str,
        topic1: str,
        subject2: str,
        topic2: str,
    ) -> AgentResponse:
        """Find TOK connections between two specific subjects/topics."""
        if self._provider == "none":
            return AgentResponse(
                content="TOK synthesis agent requires an API key.",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

        prompt = CONNECTION_PROMPT.format(
            subject1=subject1, topic1=topic1,
            subject2=subject2, topic2=topic2,
        )

        try:
            response_text = self._call_llm(prompt)

            return AgentResponse(
                content=response_text,
                agent=self.AGENT_NAME,
                confidence=0.8,
                metadata={
                    "subject1": subject1,
                    "topic1": topic1,
                    "subject2": subject2,
                    "topic2": topic2,
                },
                follow_up="Would you like me to develop one of these connections into a full TOK argument?",
            )
        except Exception as e:
            return AgentResponse(
                content=f"Error finding connections: {e}",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

    def map_aok(self, subject: str) -> dict:
        """Map an IB subject to its Areas of Knowledge and Ways of Knowing."""
        from seed_aok_mappings import AOK_MAPPINGS

        subject_key = subject.lower().replace(" ", "_").split(":")[0].strip()

        # Try exact match first
        for key, mapping in AOK_MAPPINGS.items():
            if key.lower().replace(" ", "_").split(":")[0] == subject_key:
                return mapping

        # Try partial match
        for key, mapping in AOK_MAPPINGS.items():
            if subject_key in key.lower().replace(" ", "_"):
                return mapping

        # Default
        return {
            "aok": "General",
            "primary_wok": ["Reason"],
            "secondary_wok": ["Language"],
        }

    def _build_subject_topics(
        self, subjects: list[dict], user_id: int | None
    ) -> str:
        """Build detailed subject + recent topics + AoK mapping string."""
        parts = []
        for s in subjects:
            name = s.get("name", "")
            level = s.get("level", "")
            aok_info = self.map_aok(name)

            part = (
                f"- {name} {level}: "
                f"AoK = {aok_info['aok']}, "
                f"Primary WoK = {', '.join(aok_info['primary_wok'])}"
            )

            # Get recent topics from knowledge graph if available
            if user_id:
                try:
                    from knowledge_graph import SyllabusGraph
                    graph = SyllabusGraph(name)
                    mastery = graph.get_mastery_map(user_id)
                    recent = [
                        t for t, info in mastery.items()
                        if info.get("mastery_state") in ("learning", "partial", "mastered")
                    ][:3]
                    if recent:
                        part += f", Recent topics: {', '.join(recent)}"
                except Exception:
                    pass

            parts.append(part)

        return "\n".join(parts) if parts else "No subject details available"

    def _store_aok_memories(
        self, user_id: int, subjects: list[dict]
    ) -> None:
        """Store Area of Knowledge mappings in student memory."""
        try:
            from memory import StudentMemory

            mem = StudentMemory(user_id)
            for s in subjects:
                name = s.get("name", "")
                aok_info = self.map_aok(name)
                mem.remember(
                    "area_of_knowledge",
                    f"aok_{name.lower().replace(' ', '_')}",
                    f"{name} maps to {aok_info['aok']} (AoK), "
                    f"primary WoK: {', '.join(aok_info['primary_wok'])}",
                    source="tok_synthesis",
                    confidence=1.0,
                )
        except Exception:
            pass

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
