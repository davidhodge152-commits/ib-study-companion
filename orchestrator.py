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
    # Differentiator intents
    "analyze_handwriting",
    "practice_oral",
    "check_feasibility",
    "analyze_data",
    "tok_synthesis",
    "generate_questions",
    "get_plan",
    "admissions",
]

CLASSIFICATION_PROMPT = """Classify the student's message into exactly one intent.

Intents:
- grade_answer: Student wants their answer graded/marked (they provide a question + their answer)
- explain_concept: Student wants a concept explained or wants to understand something
- help_question: Student needs help solving or approaching a specific question
- review_coursework: Student wants feedback on IA/EE/TOK writing
- find_research: Student wants real-world examples, case studies, or citations
- solve_stem: Student has a math/physics/chemistry calculation or wants a numerical answer verified
- analyze_handwriting: Student wants their handwritten work analyzed or checked
- practice_oral: Student wants to practice an Individual Oral or oral exam
- check_feasibility: Student wants to check if a coursework topic is feasible
- analyze_data: Student wants help analyzing experimental data or running statistics
- tok_synthesis: Student wants help connecting subjects for TOK or finding cross-curricular links
- generate_questions: Student wants practice questions generated
- get_plan: Student wants a study plan, daily briefing, or is stressed about studying
- admissions: Student wants help with university applications, personal statements, or UCAS/Common App
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
            elif name == "vision":
                from agents.vision_agent import VisionAgent
                self._agents[name] = VisionAgent()
            elif name == "oral":
                from agents.oral_exam_agent import OralExamAgent
                self._agents[name] = OralExamAgent(self.rag_engine)
            elif name == "coursework_ide":
                from agents.coursework_ide_agent import CourseworkIDEAgent
                self._agents[name] = CourseworkIDEAgent(self.rag_engine)
            elif name == "tok":
                from agents.tok_synthesis_agent import TOKSynthesisAgent
                self._agents[name] = TOKSynthesisAgent(self.rag_engine)
            elif name == "question_gen":
                from agents.question_gen_agent import QuestionGenAgent
                self._agents[name] = QuestionGenAgent(self.rag_engine)
            elif name == "executive":
                from agents.executive_agent import ExecutiveAgent
                self._agents[name] = ExecutiveAgent(self.rag_engine)
            elif name == "admissions":
                from agents.admissions_agent import AdmissionsAgent
                self._agents[name] = AdmissionsAgent(self.rag_engine)
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

        # TOK synthesis (check before coursework to avoid overlap)
        tok_keywords = ["tok essay", "connect subjects", "areas of knowledge",
                         "ways of knowing", "cross-curricular", "tok connection",
                         "tok exhibition"]
        if any(kw in msg_lower for kw in tok_keywords):
            return "tok_synthesis"

        # Coursework review
        cw_keywords = ["review my ia", "review my ee", "review my essay",
                        "feedback on my ia", "feedback on my ee",
                        "internal assessment"]
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

        # Handwriting analysis
        hw_keywords = ["check my working", "photo of my work", "handwriting",
                        "my working out", "analyze my working", "check my work"]
        if any(kw in msg_lower for kw in hw_keywords):
            return "analyze_handwriting"

        # Oral exam practice
        oral_keywords = ["oral exam", "io practice", "individual oral",
                          "oral presentation", "practice oral", "mock oral"]
        if any(kw in msg_lower for kw in oral_keywords):
            return "practice_oral"

        # Topic feasibility
        feasibility_keywords = ["feasibility", "is this a good topic",
                                 "good ia topic", "good ee topic", "topic idea"]
        if any(kw in msg_lower for kw in feasibility_keywords):
            return "check_feasibility"

        # Data analysis
        data_keywords = ["analyze my data", "run statistics", "statistical test",
                          "chi-squared", "t-test", "pearson correlation", "analyze data"]
        if any(kw in msg_lower for kw in data_keywords):
            return "analyze_data"

        # Question generation
        qgen_keywords = ["give me questions", "practice questions",
                          "more questions like this", "generate questions",
                          "parametric", "question variants"]
        if any(kw in msg_lower for kw in qgen_keywords):
            return "generate_questions"

        # Admissions / university applications
        admissions_keywords = ["personal statement", "university application",
                                "ucas", "common app", "college admissions",
                                "university recommendation", "admissions profile"]
        if any(kw in msg_lower for kw in admissions_keywords):
            return "admissions"

        # Study plan / executive function
        plan_keywords = ["study plan", "what should i study", "daily plan",
                          "i'm stressed", "burnout", "reprioritize",
                          "daily briefing", "weekly plan"]
        if any(kw in msg_lower for kw in plan_keywords):
            return "get_plan"

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
        elif intent == "analyze_handwriting":
            response = self._route_vision(message, context)
        elif intent == "practice_oral":
            response = self._route_oral(message, context)
        elif intent == "check_feasibility":
            response = self._route_feasibility(message, context)
        elif intent == "analyze_data":
            response = self._route_data_analysis(message, context)
        elif intent == "tok_synthesis":
            response = self._route_tok(message, context)
        elif intent == "generate_questions":
            response = self._route_question_gen(message, context)
        elif intent == "get_plan":
            response = self._route_executive(message, context)
        elif intent == "admissions":
            response = self._route_admissions(message, context)
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

    def _route_vision(self, message: str, context: dict) -> AgentResponse:
        agent = self._get_agent("vision")
        if not agent:
            return AgentResponse(
                content="Vision agent unavailable.",
                agent="vision_agent",
                confidence=0.0,
            )
        image_data = context.get("image_data", b"")
        if not image_data:
            return AgentResponse(
                content="Please upload a photo of your handwritten work so I can analyze it.",
                agent="vision_agent",
                confidence=0.5,
            )
        return agent.analyze_handwriting(
            image_data=image_data,
            question=context.get("question", message),
            subject=context.get("subject", "Mathematics"),
            marks=int(context.get("marks", 4)),
            command_term=context.get("command_term", ""),
            user_id=self.user_id,
        )

    def _route_oral(self, message: str, context: dict) -> AgentResponse:
        agent = self._get_agent("oral")
        if not agent:
            return AgentResponse(
                content="Oral exam agent unavailable.",
                agent="oral_exam_agent",
                confidence=0.0,
            )
        # Check if there's an active session
        session_state = context.get("session_state")
        if session_state:
            return agent.listen_and_respond(
                transcript=message,
                session_state=session_state,
                user_id=self.user_id,
                session_id=context.get("session_id"),
            )
        # Start new session
        return agent.start_session(
            subject=context.get("subject", "English A"),
            text_title=context.get("text_title", ""),
            text_extract=context.get("text_extract", ""),
            global_issue=context.get("global_issue", ""),
            level=context.get("level", "HL"),
            user_id=self.user_id,
        )

    def _route_feasibility(self, message: str, context: dict) -> AgentResponse:
        agent = self._get_agent("coursework_ide")
        if not agent:
            return AgentResponse(
                content="Coursework IDE agent unavailable.",
                agent="coursework_ide_agent",
                confidence=0.0,
            )
        return agent.check_feasibility(
            topic_proposal=context.get("text", message),
            subject=context.get("subject", ""),
            doc_type=context.get("doc_type", "ia"),
            school_constraints=context.get("school_constraints", ""),
        )

    def _route_data_analysis(self, message: str, context: dict) -> AgentResponse:
        agent = self._get_agent("coursework_ide")
        if not agent:
            return AgentResponse(
                content="Coursework IDE agent unavailable.",
                agent="coursework_ide_agent",
                confidence=0.0,
            )
        return agent.analyze_data(
            raw_data=context.get("data", message),
            subject=context.get("subject", ""),
            hypothesis=context.get("hypothesis", ""),
            user_id=self.user_id,
            session_id=context.get("session_id"),
        )

    def _route_tok(self, message: str, context: dict) -> AgentResponse:
        agent = self._get_agent("tok")
        if not agent:
            return AgentResponse(
                content="TOK synthesis agent unavailable.",
                agent="tok_synthesis_agent",
                confidence=0.0,
            )
        # Build student subjects from profile
        student_subjects = context.get("subjects", [])
        if not student_subjects:
            try:
                from db_stores import StudentProfileDB
                profile = StudentProfileDB(self.user_id)
                student_subjects = [
                    {"name": s.name, "level": s.level} for s in profile.subjects
                ]
            except Exception:
                pass

        return agent.synthesize(
            message=message,
            student_subjects=student_subjects,
            tok_prompt=context.get("tok_prompt", ""),
            user_id=self.user_id,
        )

    def _route_question_gen(self, message: str, context: dict) -> AgentResponse:
        agent = self._get_agent("question_gen")
        if not agent:
            return AgentResponse(
                content="Question generation agent unavailable.",
                agent="question_gen_agent",
                confidence=0.0,
            )
        return agent.generate_parametric(
            subject=context.get("subject", "Mathematics"),
            topic=context.get("topic", ""),
            source_question=context.get("question", message),
            variation_type=context.get("variation_type", "numbers"),
            count=int(context.get("count", 3)),
            difficulty=context.get("difficulty", "medium"),
        )

    def _route_executive(self, message: str, context: dict) -> AgentResponse:
        agent = self._get_agent("executive")
        if not agent:
            return AgentResponse(
                content="Executive agent unavailable.",
                agent="executive_agent",
                confidence=0.0,
            )
        # Determine which executive function is needed
        msg_lower = message.lower()
        if any(kw in msg_lower for kw in ("reprioritize", "deadline moved", "changed")):
            return agent.reprioritize(self.user_id, message)
        elif any(kw in msg_lower for kw in ("study plan", "weekly plan", "generate plan")):
            return agent.generate_smart_plan(
                self.user_id,
                days_ahead=int(context.get("days_ahead", 7)),
            )
        else:
            return agent.daily_briefing(self.user_id)

    def _route_admissions(self, message: str, context: dict) -> AgentResponse:
        agent = self._get_agent("admissions")
        if not agent:
            return AgentResponse(
                content="Admissions agent unavailable.",
                agent="admissions_agent",
                confidence=0.0,
            )
        msg_lower = message.lower()
        if any(kw in msg_lower for kw in ("personal statement", "draft")):
            return agent.draft_personal_statement(
                self.user_id,
                target=context.get("target", "common_app"),
                word_limit=int(context.get("word_limit", 650)),
            )
        elif any(kw in msg_lower for kw in ("suggest", "recommend", "university")):
            return agent.suggest_universities(
                self.user_id,
                preferences=context.get("preferences"),
            )
        else:
            return agent.generate_profile(self.user_id)

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
