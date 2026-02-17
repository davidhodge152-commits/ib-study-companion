"""Oral Exam Agent — Live Individual Oral roleplay.

Simulates the IB Individual Oral examination with adaptive examiner
questioning, session state tracking (prepared response + follow-up phases),
and criterion-by-criterion rubric grading.
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

EXAMINER_SYSTEM = """You are an experienced IB {subject} oral examiner conducting an Individual Oral.

TEXT: {text_title}
EXTRACT: {text_extract}
GLOBAL ISSUE: {global_issue}
LEVEL: {level}

PHASE: {phase}

YOUR ROLE:
- During PREPARED phase: Listen carefully. Note the student's key claims,
  evidence used, and analytical points. Do NOT interrupt.
- During FOLLOW_UP phase: Ask probing, challenging questions based on gaps
  you identified. Push the student to go deeper.

EXAMINER BEHAVIORS:
1. Ask ONE question at a time
2. Use IB command terms: "Can you elaborate?", "How does this connect to...?",
   "What evidence supports...?", "To what extent...?"
3. Follow up on vague claims with specifics
4. Challenge assertions that lack textual evidence
5. Test understanding of both the text and the global issue
6. Be encouraging but rigorous

{phase_instruction}"""

FOLLOW_UP_INSTRUCTION = """You are now in the FOLLOW-UP DISCUSSION phase (5 minutes).

The student has made these claims so far:
{student_claims}

Gaps identified in their prepared response:
{gaps}

Ask a probing question that addresses the most significant gap.
Return ONLY your examiner question (1-2 sentences). Nothing else."""

GRADING_SYSTEM = """You are grading an IB Individual Oral based on the full transcript.

SUBJECT: {subject}
LEVEL: {level}
TEXT: {text_title}
GLOBAL ISSUE: {global_issue}

GRADING CRITERIA FOR {rubric_type}:
{criteria}

FULL TRANSCRIPT:
{transcript}

Grade each criterion. For EACH criterion provide:
CRITERION: [name]
SCORE: [earned] / [max]
JUSTIFICATION: [2-3 sentences explaining the score with specific references to the transcript]
IMPROVEMENT: [1 specific actionable suggestion]

Then provide:
TOTAL: [total earned] / [total possible]
OVERALL_FEEDBACK: [3-4 sentences of holistic feedback]
TOP_PRIORITIES:
1. [most impactful improvement]
2. [second most impactful]
3. [third most impactful]"""

# IB Oral rubrics
ORAL_RUBRICS = {
    "language_a": {
        "criteria": [
            ("Knowledge and understanding", 10),
            ("Analysis and evaluation", 10),
            ("Focus and organization", 10),
            ("Language", 10),
        ],
        "total": 40,
    },
    "language_b": {
        "criteria": [
            ("Productive skills", 12),
            ("Interactive skills", 12),
            ("Language range and accuracy", 6),
        ],
        "total": 30,
    },
}

LANGUAGE_A_SUBJECTS = {"english_a", "english", "french_a", "spanish_a", "literature"}
LANGUAGE_B_SUBJECTS = {"english_b", "french_b", "spanish_b", "french", "spanish",
                       "mandarin_b", "german_b"}


class OralExamAgent:
    """Simulates IB Individual Oral examination."""

    AGENT_NAME = "oral_exam_agent"

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

    def _get_rubric_type(self, subject: str) -> str:
        """Determine rubric type from subject."""
        subj_key = subject.lower().replace(" ", "_").split(":")[0]
        if subj_key in LANGUAGE_B_SUBJECTS:
            return "language_b"
        return "language_a"

    def start_session(
        self,
        subject: str,
        text_title: str,
        text_extract: str = "",
        global_issue: str = "",
        level: str = "HL",
        user_id: int | None = None,
    ) -> AgentResponse:
        """Start a new oral exam practice session."""
        if self._provider == "none":
            return AgentResponse(
                content="Oral exam agent requires an API key (Anthropic or Google).",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

        session_state = {
            "subject": subject,
            "text_title": text_title,
            "text_extract": text_extract,
            "global_issue": global_issue,
            "level": level,
            "phase": "prepared",
            "transcript": [],
            "student_claims": [],
            "examiner_questions": [],
            "gaps": [],
        }

        # Save session to database
        session_id = None
        if user_id:
            session_id = self._save_session(user_id, session_state)

        opening = (
            f"## Individual Oral Practice — {subject} {level}\n\n"
            f"**Text:** {text_title}\n"
            f"**Global Issue:** {global_issue}\n\n"
            "---\n\n"
            "You now have **10 minutes** for your prepared response.\n\n"
            "Begin by introducing your text and global issue, then present "
            "your analysis. I will listen carefully and take notes.\n\n"
            "*When you're ready, share your prepared response. "
            "Type your response as if you were speaking to the examiner.*"
        )

        return AgentResponse(
            content=opening,
            agent=self.AGENT_NAME,
            confidence=0.9,
            metadata={
                "session_id": session_id,
                "session_state": session_state,
                "phase": "prepared",
            },
        )

    def listen_and_respond(
        self,
        transcript: str,
        session_state: dict,
        user_id: int | None = None,
        session_id: int | None = None,
    ) -> AgentResponse:
        """Process student's response and generate examiner follow-up."""
        if self._provider == "none":
            return AgentResponse(
                content="Oral exam agent requires an API key.",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

        phase = session_state.get("phase", "prepared")
        subject = session_state.get("subject", "")
        text_title = session_state.get("text_title", "")
        text_extract = session_state.get("text_extract", "")
        global_issue = session_state.get("global_issue", "")
        level = session_state.get("level", "HL")

        # Add to transcript
        session_state.setdefault("transcript", []).append({
            "role": "student",
            "content": transcript,
            "phase": phase,
        })

        # Extract claims from student's response
        claims = self._extract_claims(transcript)
        session_state.setdefault("student_claims", []).extend(claims)

        if phase == "prepared":
            # After prepared response, transition to follow-up
            session_state["phase"] = "follow_up"
            gaps = self._identify_gaps(
                session_state["student_claims"],
                text_title, global_issue, subject
            )
            session_state["gaps"] = gaps

            # Generate first examiner question
            question = self._generate_follow_up(
                session_state["student_claims"],
                gaps,
                text_extract or text_title,
                subject,
                level,
                session_state.get("examiner_questions", []),
            )
            session_state.setdefault("examiner_questions", []).append(question)
            session_state["transcript"].append({
                "role": "examiner",
                "content": question,
                "phase": "follow_up",
            })

            response_text = (
                "Thank you for your prepared response. I noted several "
                "interesting points.\n\n"
                "We'll now move to the **follow-up discussion** (5 minutes).\n\n"
                f"**Examiner:** {question}"
            )
        else:
            # Generate next follow-up question
            gaps = session_state.get("gaps", [])
            question = self._generate_follow_up(
                session_state["student_claims"],
                gaps,
                text_extract or text_title,
                subject,
                level,
                session_state.get("examiner_questions", []),
            )
            session_state.setdefault("examiner_questions", []).append(question)
            session_state["transcript"].append({
                "role": "examiner",
                "content": question,
                "phase": "follow_up",
            })
            response_text = f"**Examiner:** {question}"

        # Update database
        if user_id and session_id:
            self._update_session(session_id, session_state)

        return AgentResponse(
            content=response_text,
            agent=self.AGENT_NAME,
            confidence=0.85,
            metadata={
                "session_id": session_id,
                "session_state": session_state,
                "phase": session_state["phase"],
                "claims_count": len(session_state.get("student_claims", [])),
            },
        )

    def grade_oral(
        self,
        session_state: dict,
        user_id: int | None = None,
        session_id: int | None = None,
    ) -> AgentResponse:
        """Grade the completed oral session against IB rubric."""
        if self._provider == "none":
            return AgentResponse(
                content="Oral exam agent requires an API key.",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

        subject = session_state.get("subject", "")
        level = session_state.get("level", "HL")
        text_title = session_state.get("text_title", "")
        global_issue = session_state.get("global_issue", "")
        transcript_entries = session_state.get("transcript", [])

        rubric_type = self._get_rubric_type(subject)
        rubric = ORAL_RUBRICS[rubric_type]

        criteria_text = "\n".join(
            f"- {name}: {max_marks} marks" for name, max_marks in rubric["criteria"]
        )

        transcript_text = "\n".join(
            f"{'Student' if t['role'] == 'student' else 'Examiner'}: {t['content']}"
            for t in transcript_entries
        )

        prompt = GRADING_SYSTEM.format(
            subject=subject,
            level=level,
            text_title=text_title,
            global_issue=global_issue,
            rubric_type=rubric_type.replace("_", " ").title(),
            criteria=criteria_text,
            transcript=transcript_text,
        )

        try:
            response_text = self._call_llm(prompt)
            criterion_scores = self._parse_grading(response_text, rubric)

            total_earned = sum(s.get("earned", 0) for s in criterion_scores.values())
            total_possible = rubric["total"]

            # Save final grades
            if user_id and session_id:
                session_state["criterion_scores"] = criterion_scores
                session_state["total_score"] = total_earned
                session_state["feedback"] = response_text
                session_state["completed_at"] = datetime.now().isoformat()
                self._update_session(session_id, session_state)

            content = (
                f"## Oral Exam Results — {subject} {level}\n\n"
                f"**Total: {total_earned}/{total_possible}**\n\n"
                f"{response_text}"
            )

            return AgentResponse(
                content=content,
                agent=self.AGENT_NAME,
                confidence=0.85,
                metadata={
                    "session_id": session_id,
                    "criterion_scores": criterion_scores,
                    "total_score": total_earned,
                    "total_possible": total_possible,
                    "rubric_type": rubric_type,
                },
                follow_up="Would you like to practice another oral, or work on a specific weak area?",
            )
        except Exception as e:
            return AgentResponse(
                content=f"Error grading oral: {e}",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

    def _extract_claims(self, text: str) -> list[str]:
        """Extract key claims/arguments from student's response."""
        try:
            prompt = (
                "Extract the key claims and arguments from this oral response. "
                "Return a JSON array of strings, each being one claim.\n\n"
                f"Response: {text[:3000]}\n\nReturn ONLY the JSON array."
            )
            raw = self._call_llm(prompt)
            if "```" in raw:
                start = raw.index("[")
                end = raw.rindex("]") + 1
                raw = raw[start:end]
            claims = json.loads(raw)
            return claims if isinstance(claims, list) else []
        except Exception:
            # Fallback: split into sentences
            sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 20]
            return sentences[:5]

    def _identify_gaps(
        self, claims: list[str], text_title: str,
        global_issue: str, subject: str
    ) -> list[str]:
        """Identify gaps in the student's analysis."""
        try:
            prompt = (
                f"An IB {subject} student analyzed '{text_title}' in relation to "
                f"the global issue '{global_issue}'.\n\n"
                f"Their claims: {json.dumps(claims[:10])}\n\n"
                "What important aspects did they miss? Return a JSON array of "
                "gaps (strings). Focus on:\n"
                "- Missing textual evidence\n"
                "- Unexamined authorial choices\n"
                "- Weak connections to global issue\n"
                "- Lack of counter-arguments\n\n"
                "Return ONLY the JSON array."
            )
            raw = self._call_llm(prompt)
            if "[" in raw:
                start = raw.index("[")
                end = raw.rindex("]") + 1
                gaps = json.loads(raw[start:end])
                return gaps if isinstance(gaps, list) else []
        except Exception:
            pass
        return ["Need more textual evidence", "Explore authorial choices"]

    def _generate_follow_up(
        self,
        claims: list[str],
        gaps: list[str],
        text_context: str,
        subject: str,
        level: str,
        previous_questions: list[str],
    ) -> str:
        """Generate an examiner follow-up question."""
        prev_q = "\n".join(f"- {q}" for q in previous_questions) if previous_questions else "None yet"

        prompt = (
            f"You are an IB {subject} {level} oral examiner.\n\n"
            f"Student claims: {json.dumps(claims[-5:])}\n"
            f"Gaps to probe: {json.dumps(gaps[:3])}\n"
            f"Previous questions asked: {prev_q}\n\n"
            "Ask ONE probing follow-up question that:\n"
            "1. Addresses a gap not yet covered by previous questions\n"
            "2. Pushes the student to deepen their analysis\n"
            "3. Uses an IB command term (elaborate, evaluate, to what extent)\n\n"
            "Return ONLY the question (1-2 sentences)."
        )

        try:
            return self._call_llm(prompt).strip().strip('"')
        except Exception:
            return "Can you elaborate on how this connects to your chosen global issue?"

    def _call_llm(self, prompt: str, system: str = "") -> str:
        """Call the configured LLM provider with resilience."""
        from ai_resilience import resilient_llm_call

        model = "claude-sonnet-4-5-20250929" if self._provider == "claude" else "gemini-2.0-flash"
        text, _ = resilient_llm_call(self._provider, model, prompt, system=system)
        return text

    def _parse_grading(self, raw: str, rubric: dict) -> dict:
        """Parse grading response into criterion scores."""
        scores = {}
        current_criterion = None

        for line in raw.splitlines():
            stripped = line.strip()
            if stripped.startswith("CRITERION:"):
                current_criterion = stripped.split(":", 1)[1].strip()
                scores[current_criterion] = {"earned": 0, "max": 0, "justification": "", "improvement": ""}
            elif stripped.startswith("SCORE:") and current_criterion:
                try:
                    parts = stripped.split(":", 1)[1].strip().split("/")
                    scores[current_criterion]["earned"] = int(parts[0].strip())
                    scores[current_criterion]["max"] = int(parts[1].strip())
                except (ValueError, IndexError):
                    pass
            elif stripped.startswith("JUSTIFICATION:") and current_criterion:
                scores[current_criterion]["justification"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("IMPROVEMENT:") and current_criterion:
                scores[current_criterion]["improvement"] = stripped.split(":", 1)[1].strip()

        return scores

    def _save_session(self, user_id: int, state: dict) -> int | None:
        """Save a new oral session to the database."""
        try:
            from database import get_db

            db = get_db()
            cursor = db.execute(
                "INSERT INTO oral_sessions "
                "(user_id, subject, level, text_title, global_issue, phase, "
                "started_at, transcript, examiner_questions, student_claims) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    user_id,
                    state.get("subject", ""),
                    state.get("level", "HL"),
                    state.get("text_title", ""),
                    state.get("global_issue", ""),
                    state.get("phase", "prepared"),
                    datetime.now().isoformat(),
                    json.dumps(state.get("transcript", [])),
                    json.dumps(state.get("examiner_questions", [])),
                    json.dumps(state.get("student_claims", [])),
                ),
            )
            db.commit()
            return cursor.lastrowid
        except Exception:
            return None

    def _update_session(self, session_id: int, state: dict) -> None:
        """Update an existing oral session."""
        try:
            from database import get_db

            db = get_db()
            db.execute(
                "UPDATE oral_sessions SET "
                "phase = ?, transcript = ?, examiner_questions = ?, "
                "student_claims = ?, criterion_scores = ?, "
                "total_score = ?, feedback = ?, completed_at = ? "
                "WHERE id = ?",
                (
                    state.get("phase", ""),
                    json.dumps(state.get("transcript", [])),
                    json.dumps(state.get("examiner_questions", [])),
                    json.dumps(state.get("student_claims", [])),
                    json.dumps(state.get("criterion_scores", {})),
                    state.get("total_score", 0),
                    state.get("feedback", ""),
                    state.get("completed_at", ""),
                    session_id,
                ),
            )
            db.commit()
        except Exception:
            pass
