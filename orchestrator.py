"""Orchestrator — The Head Tutor.

Receives all student interactions, classifies intent, builds context,
and routes to the appropriate sub-agent.
"""

from __future__ import annotations

import os
import time
from datetime import datetime

from dotenv import load_dotenv

from agents.base import AgentResponse

load_dotenv()

INTENT_LABELS = [
    "grade_answer",
    "explain_concept",
    "help_question",
    "review_coursework",
    "find_research",
    "solve_stem",
    "general_chat",
]

CLASSIFICATION_PROMPT = """Classify the student's message into exactly one intent.

Intents:
- grade_answer: Student wants their answer graded/marked (they provide a question + their answer)
- explain_concept: Student wants a concept explained or wants to understand something
- help_question: Student needs help solving or approaching a specific question
- review_coursework: Student wants feedback on IA/EE/TOK writing
- find_research: Student wants real-world examples, case studies, or citations
- solve_stem: Student has a math/physics/chemistry calculation or wants a numerical answer verified
- general_chat: Anything else (greetings, meta-questions, etc.)

Context: Subject={subject}, Topic={topic}

Student message: {message}

Respond with ONLY the intent label (e.g., "explain_concept"). Nothing else."""

STEM_SUBJECTS = {
    "mathematics", "math", "mathematics:_aa", "mathematics:_ai",
    "mathematics: aa", "mathematics: ai", "math_aa", "math_ai",
    "physics", "chemistry",
}


class Orchestrator:
    """Central routing engine for the compound AI system."""

    def __init__(self, user_id: int, rag_engine=None) -> None:
        self.user_id = user_id
        self.rag_engine = rag_engine
        self._agents: dict = {}

    def _get_agent(self, name: str):
        """Lazy-load agents on demand."""
        if name not in self._agents:
            if name == "grading":
                from agents.grading_agent import GradingAgent
                self._agents[name] = GradingAgent(self.rag_engine)
            elif name == "tutor":
                from agents.tutor_agent import TutorAgent
                self._agents[name] = TutorAgent(self.rag_engine)
            elif name == "stem":
                from agents.stem_solver import STEMSolverAgent
                self._agents[name] = STEMSolverAgent()
            elif name == "coursework":
                from agents.coursework_agent import CourseworkAgent
                self._agents[name] = CourseworkAgent(self.rag_engine)
            elif name == "research":
                from agents.research_agent import ResearchAgent
                self._agents[name] = ResearchAgent()
        return self._agents.get(name)

    def classify_intent(
        self, message: str, context: dict | None = None
    ) -> str:
        """Classify the student's intent using Gemini."""
        context = context or {}
        subject = context.get("subject", "")
        topic = context.get("topic", "")

        # Fast heuristic classification (avoids LLM call for obvious cases)
        msg_lower = message.lower().strip()

        # Grade answer: explicit grading request or question+answer in context
        if context.get("answer") and context.get("question"):
            return "grade_answer"
        grade_keywords = ["grade my", "mark my", "grade this", "mark this", "score my"]
        if any(kw in msg_lower for kw in grade_keywords):
            return "grade_answer"

        # Coursework review
        cw_keywords = ["review my ia", "review my ee", "review my essay",
                        "feedback on my ia", "feedback on my ee",
                        "tok essay", "tok exhibition", "internal assessment"]
        if any(kw in msg_lower for kw in cw_keywords):
            return "review_coursework"

        # Research / examples
        research_keywords = ["find examples", "real-world example", "case study",
                             "cite", "citation", "find research", "find sources"]
        if any(kw in msg_lower for kw in research_keywords):
            return "find_research"

        # STEM solving
        stem_keywords = ["calculate", "solve", "compute", "what is the value",
                         "find x", "find the", "derive", "integrate", "differentiate"]
        if (any(kw in msg_lower for kw in stem_keywords) and
                subject.lower().replace(" ", "_").split(":")[0] in STEM_SUBJECTS):
            return "solve_stem"

        # If context has a question (help with a specific question)
        if context.get("question") and not context.get("answer"):
            return "help_question"

        # Explain concept
        explain_keywords = ["explain", "what is", "what are", "how does",
                            "why does", "tell me about", "help me understand"]
        if any(kw in msg_lower for kw in explain_keywords):
            return "explain_concept"

        # Fall back to LLM classification for ambiguous cases
        return self._llm_classify(message, subject, topic)

    def _llm_classify(self, message: str, subject: str, topic: str) -> str:
        """Use Gemini for ambiguous intent classification."""
        google_key = os.getenv("GOOGLE_API_KEY")
        if not google_key:
            return "general_chat"

        try:
            import google.generativeai as genai

            genai.configure(api_key=google_key)
            model = genai.GenerativeModel("gemini-2.0-flash")
            prompt = CLASSIFICATION_PROMPT.format(
                subject=subject or "General",
                topic=topic or "General",
                message=message,
            )
            response = model.generate_content(prompt)
            intent = response.text.strip().lower().replace('"', "").replace("'", "")

            if intent in INTENT_LABELS:
                return intent
        except Exception:
            pass

        return "general_chat"

    def route(
        self,
        intent: str,
        message: str,
        context: dict | None = None,
        messages: list[dict] | None = None,
    ) -> AgentResponse:
        """Dispatch to the correct sub-agent."""
        context = context or {}
        start = time.time()

        if intent == "grade_answer":
            response = self._route_grading(message, context)
        elif intent in ("explain_concept", "help_question", "general_chat"):
            response = self._route_tutor(message, context, messages)
        elif intent == "solve_stem":
            response = self._route_stem(message, context)
        elif intent == "review_coursework":
            response = self._route_coursework(message, context)
        elif intent == "find_research":
            response = self._route_research(message, context)
        else:
            response = self._route_tutor(message, context, messages)

        # Log agent interaction
        latency_ms = int((time.time() - start) * 1000)
        self._log_interaction(intent, response, message, latency_ms)

        # Auto-extract memories after tutor conversations (Phase 4)
        if intent in ("explain_concept", "help_question", "general_chat") and messages:
            try:
                from memory import StudentMemory

                mem = StudentMemory(self.user_id)
                mem.auto_extract(messages + [{"role": "assistant", "content": response.content}])
            except (ImportError, Exception):
                pass

        return response

    def _route_grading(self, message: str, context: dict) -> AgentResponse:
        agent = self._get_agent("grading")
        if not agent:
            return AgentResponse(
                content="Grading agent unavailable.",
                agent="grading_agent",
                confidence=0.0,
            )
        return agent.grade(
            question=context.get("question", message),
            answer=context.get("answer", message),
            subject=context.get("subject", "").lower().split(":")[0].strip().replace(" ", "_"),
            marks=int(context.get("marks", 4)),
            command_term=context.get("command_term", ""),
            subject_display=context.get("subject", ""),
            user_id=self.user_id,
        )

    def _route_tutor(
        self, message: str, context: dict, messages: list[dict] | None
    ) -> AgentResponse:
        agent = self._get_agent("tutor")
        if not agent:
            return AgentResponse(
                content="Tutor agent unavailable.",
                agent="tutor_agent",
                confidence=0.0,
            )

        # Build conversation history
        conv_messages = messages or []
        if not conv_messages or (conv_messages and conv_messages[-1].get("content") != message):
            conv_messages = conv_messages + [{"role": "user", "content": message}]

        # Get student's ability theta
        ability_theta = 0.0
        try:
            from db_stores import StudentAbilityStoreDB

            store = StudentAbilityStoreDB(self.user_id)
            ability = store.get_theta(
                context.get("subject", ""),
                context.get("topic", ""),
            )
            ability_theta = ability.get("theta", 0.0)
        except Exception:
            pass

        # Get misconceptions
        misconceptions = []
        try:
            from db_stores import MisconceptionLogDB

            log = MisconceptionLogDB(self.user_id)
            for m in log.recent(limit=5):
                misconceptions.append(m.get("pattern_id", ""))
        except Exception:
            pass

        # Get semantic memory (Phase 4)
        memory_context = ""
        try:
            from memory import StudentMemory

            mem = StudentMemory(self.user_id)
            memory_context = mem.recall_for_prompt(context.get("subject", ""))
        except (ImportError, Exception):
            pass

        return agent.tutor(
            messages=conv_messages,
            subject=context.get("subject", "General"),
            topic=context.get("topic", "General"),
            ability_theta=ability_theta,
            memory_context=memory_context,
            misconceptions=misconceptions if misconceptions else None,
        )

    def _route_stem(self, message: str, context: dict) -> AgentResponse:
        agent = self._get_agent("stem")
        if not agent:
            return AgentResponse(
                content="STEM solver unavailable.",
                agent="stem_solver",
                confidence=0.0,
            )
        return agent.solve(
            question=context.get("question", message),
            student_work=context.get("answer", ""),
            subject=context.get("subject", "Mathematics"),
        )

    def _route_coursework(self, message: str, context: dict) -> AgentResponse:
        agent = self._get_agent("coursework")
        if not agent:
            return AgentResponse(
                content="Coursework agent unavailable.",
                agent="coursework_agent",
                confidence=0.0,
            )
        return agent.review(
            text=context.get("text", message),
            doc_type=context.get("doc_type", "ia"),
            subject=context.get("subject", ""),
            criterion=context.get("criterion", ""),
        )

    def _route_research(self, message: str, context: dict) -> AgentResponse:
        agent = self._get_agent("research")
        if not agent:
            return AgentResponse(
                content="Research agent unavailable.",
                agent="research_agent",
                confidence=0.0,
            )
        return agent.find_examples(
            topic=context.get("topic", message),
            subject=context.get("subject", ""),
            count=int(context.get("count", 3)),
            doc_type=context.get("doc_type", ""),
        )

    def build_context(self) -> dict:
        """Build full student context for agent prompts."""
        ctx: dict = {"user_id": self.user_id}
        try:
            from db_stores import StudentProfileDB, StudentAbilityStoreDB

            profile = StudentProfileDB(self.user_id)
            ctx["name"] = profile.name
            ctx["subjects"] = [
                {"name": s.name, "level": s.level, "target": s.target_grade}
                for s in profile.subjects
            ]
            ctx["exam_session"] = profile.exam_session
        except Exception:
            pass

        return ctx

    def _log_interaction(
        self,
        intent: str,
        response: AgentResponse,
        input_summary: str,
        latency_ms: int,
    ) -> None:
        """Log agent interaction to database."""
        try:
            from database import get_db

            db = get_db()
            db.execute(
                "INSERT INTO agent_interactions "
                "(user_id, intent, agent, confidence, input_summary, "
                "response_summary, latency_ms, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    self.user_id,
                    intent,
                    response.agent,
                    response.confidence,
                    input_summary[:200],
                    response.content[:200],
                    latency_ms,
                    datetime.now().isoformat(),
                ),
            )
            db.commit()
        except Exception:
            pass  # Logging is best-effort
