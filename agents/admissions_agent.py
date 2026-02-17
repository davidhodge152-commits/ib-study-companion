"""Admissions Agent — University Application Support.

Generates admissions profiles, drafts personal statements,
and suggests university matches based on student data.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

from dotenv import load_dotenv

from agents.base import AgentResponse

load_dotenv()

PROFILE_PROMPT = """You are an IB university admissions counsellor AI.

Based on the student data below, generate a comprehensive admissions profile.

Student Data:
- Name: {name}
- Predicted IB Total: {predicted_total}/45
- Subjects: {subjects}
- Subject Strengths: {strengths}
- Extended Essay: {ee_topic}
- CAS Reflections: {cas_summary}
- Academic Interests: {interests}
- Writing Style: {writing_style}

Generate a JSON response:
{{
    "predicted_total": <int>,
    "subject_strengths": ["strength1", "strength2", ...],
    "extracurricular_summary": "...",
    "academic_interests": "...",
    "writing_style_summary": "...",
    "recommended_universities": [
        {{"name": "...", "category": "reach|match|safety", "reason": "..."}}
    ]
}}"""

PERSONAL_STATEMENT_PROMPT = """You are helping an IB student draft a personal statement.

Target: {target} ({word_limit} words max)
Student Profile:
- Name: {name}
- Predicted: {predicted_total}/45
- Subjects: {subjects}
- Strengths: {strengths}
- Extended Essay: {ee_topic}
- CAS highlights: {cas_summary}
- Academic interests: {interests}
- Writing style: {writing_style}

Write a personal statement draft in the student's authentic voice.
The statement should:
1. Open with a compelling personal anecdote or insight
2. Connect academic interests to personal experiences
3. Reference specific IB experiences (EE, CAS, subjects)
4. Show intellectual curiosity and growth
5. End with forward-looking aspirations

Write the complete statement now."""

UNIVERSITY_PROMPT = """Based on this IB student's profile, suggest universities.

Predicted IB Total: {predicted_total}/45
Subjects: {subjects}
Strengths: {strengths}
Geographic Preference: {geo_pref}
Field of Interest: {field}
Budget Sensitivity: {budget}

Provide 9 recommendations: 3 reach, 3 match, 3 safety.

Respond in JSON:
{{
    "reach": [{{"name": "...", "location": "...", "ib_requirement": <int>, "reason": "..."}}],
    "match": [{{"name": "...", "location": "...", "ib_requirement": <int>, "reason": "..."}}],
    "safety": [{{"name": "...", "location": "...", "ib_requirement": <int>, "reason": "..."}}]
}}"""


class AdmissionsAgent:
    """Generates admissions profiles and personal statements."""

    AGENT_NAME = "admissions_agent"

    def __init__(self, rag_engine=None) -> None:
        self.rag_engine = rag_engine
        self._claude_client = None
        self._gemini_model = None
        self._provider = "none"
        self._init_provider()

    def _init_provider(self) -> None:
        """Try Claude first, then Gemini fallback."""
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

    def _gather_student_data(self, user_id: int) -> dict:
        """Gather all student data for profile generation."""
        data = {
            "name": "Student", "predicted_total": 0, "subjects": [],
            "strengths": [], "ee_topic": "", "cas_summary": "",
            "interests": "", "writing_style": "",
        }

        try:
            from db_stores import StudentProfileDB
            profile = StudentProfileDB.load(user_id)
            if profile:
                data["name"] = profile.name
                data["subjects"] = [
                    f"{s.name} {s.level}" for s in profile.subjects
                ]
        except Exception:
            pass

        # Predicted total from grade averages
        try:
            from database import get_db
            db = get_db()
            rows = db.execute(
                "SELECT subject, AVG(grade) as avg_g FROM grade_details "
                "WHERE user_id = ? GROUP BY subject",
                (user_id,),
            ).fetchall()
            total = sum(round(r["avg_g"]) for r in rows if r["avg_g"])
            data["predicted_total"] = min(total, 45)

            # Subject strengths
            sorted_subj = sorted(rows, key=lambda x: x["avg_g"] or 0, reverse=True)
            data["strengths"] = [
                f"{r['subject']} (avg {round(r['avg_g'], 1)})"
                for r in sorted_subj[:3] if r["avg_g"]
            ]
        except Exception:
            pass

        # Extended Essay
        try:
            from db_stores import IBLifecycleDB
            lc = IBLifecycleDB(user_id)
            ee = lc.extended_essay
            if ee:
                data["ee_topic"] = f"{ee.subject}: {ee.research_question}" if hasattr(ee, 'research_question') else str(ee.subject)
        except Exception:
            pass

        # CAS reflections
        try:
            from db_stores import IBLifecycleDB
            lc = IBLifecycleDB(user_id)
            reflections = lc.cas_reflections
            if reflections:
                cas_items = [f"{r.title} ({r.strand})" for r in reflections[:5]]
                data["cas_summary"] = ", ".join(cas_items)
        except Exception:
            pass

        # Writing profile
        try:
            from db_stores import WritingProfileDB
            wp = WritingProfileDB(user_id)
            style = wp.style_summary()
            if style:
                data["writing_style"] = style
        except Exception:
            pass

        # Memory/interests
        try:
            from memory import StudentMemory
            mem = StudentMemory(user_id)
            interests = mem.recall_for_prompt("interests academic passions")
            if interests:
                data["interests"] = interests[:300]
        except Exception:
            pass

        return data

    def generate_profile(self, user_id: int) -> AgentResponse:
        """Generate a comprehensive admissions profile."""
        if self._provider == "none":
            return AgentResponse(
                content="Admissions agent unavailable.",
                agent=self.AGENT_NAME, confidence=0.0,
            )

        student_data = self._gather_student_data(user_id)
        prompt = PROFILE_PROMPT.format(
            name=student_data["name"],
            predicted_total=student_data["predicted_total"],
            subjects=", ".join(student_data["subjects"]),
            strengths=", ".join(student_data["strengths"]),
            ee_topic=student_data["ee_topic"],
            cas_summary=student_data["cas_summary"],
            interests=student_data["interests"],
            writing_style=student_data["writing_style"],
        )

        try:
            from ai_resilience import resilient_llm_call

            model = "claude-sonnet-4-20250514" if self._provider == "claude" else "gemini-2.0-flash"
            raw, _ = resilient_llm_call(self._provider, model, prompt)

            # Try to parse JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', raw)
            profile_data = {}
            if json_match:
                try:
                    profile_data = json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass

            # Save to DB
            self._save_profile(user_id, profile_data, student_data)

            return AgentResponse(
                content=raw,
                agent=self.AGENT_NAME,
                confidence=0.85,
                metadata={"profile": profile_data, "student_data": student_data},
            )
        except Exception as e:
            return AgentResponse(
                content=f"Error generating profile: {str(e)}",
                agent=self.AGENT_NAME, confidence=0.0,
            )

    def _save_profile(self, user_id: int, profile_data: dict, student_data: dict) -> None:
        """Save admissions profile to database."""
        try:
            from database import get_db
            db = get_db()
            now = datetime.now().isoformat()
            db.execute(
                "INSERT OR REPLACE INTO admissions_profiles "
                "(user_id, predicted_total, subject_strengths, "
                "extracurricular_summary, academic_interests, "
                "writing_style_summary, recommended_universities, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id,
                 profile_data.get("predicted_total", student_data["predicted_total"]),
                 json.dumps(profile_data.get("subject_strengths", student_data["strengths"])),
                 profile_data.get("extracurricular_summary", student_data["cas_summary"]),
                 profile_data.get("academic_interests", student_data["interests"]),
                 profile_data.get("writing_style_summary", student_data["writing_style"]),
                 json.dumps(profile_data.get("recommended_universities", [])),
                 now),
            )
            db.commit()
        except Exception:
            pass

    def draft_personal_statement(
        self, user_id: int, target: str = "common_app", word_limit: int = 650,
    ) -> AgentResponse:
        """Draft a personal statement in the student's voice."""
        if self._provider == "none":
            return AgentResponse(
                content="Admissions agent unavailable.",
                agent=self.AGENT_NAME, confidence=0.0,
            )

        student_data = self._gather_student_data(user_id)
        prompt = PERSONAL_STATEMENT_PROMPT.format(
            target=target, word_limit=word_limit,
            name=student_data["name"],
            predicted_total=student_data["predicted_total"],
            subjects=", ".join(student_data["subjects"]),
            strengths=", ".join(student_data["strengths"]),
            ee_topic=student_data["ee_topic"],
            cas_summary=student_data["cas_summary"],
            interests=student_data["interests"],
            writing_style=student_data["writing_style"],
        )

        try:
            from ai_resilience import resilient_llm_call

            model = "claude-sonnet-4-20250514" if self._provider == "claude" else "gemini-2.0-flash"
            raw, _ = resilient_llm_call(self._provider, model, prompt)

            # Save draft to profile
            try:
                from database import get_db
                db = get_db()
                db.execute(
                    "UPDATE admissions_profiles SET personal_statement_draft = ?, "
                    "updated_at = ? WHERE user_id = ?",
                    (raw, datetime.now().isoformat(), user_id),
                )
                db.commit()
            except Exception:
                pass

            return AgentResponse(
                content=raw,
                agent=self.AGENT_NAME,
                confidence=0.8,
                metadata={"target": target, "word_limit": word_limit,
                          "actual_words": len(raw.split())},
            )
        except Exception as e:
            return AgentResponse(
                content=f"Error drafting statement: {str(e)}",
                agent=self.AGENT_NAME, confidence=0.0,
            )

    def suggest_universities(
        self, user_id: int, preferences: dict | None = None,
    ) -> AgentResponse:
        """Suggest reach/match/safety universities."""
        if self._provider == "none":
            return AgentResponse(
                content="Admissions agent unavailable.",
                agent=self.AGENT_NAME, confidence=0.0,
            )

        prefs = preferences or {}
        student_data = self._gather_student_data(user_id)

        prompt = UNIVERSITY_PROMPT.format(
            predicted_total=student_data["predicted_total"],
            subjects=", ".join(student_data["subjects"]),
            strengths=", ".join(student_data["strengths"]),
            geo_pref=prefs.get("location", "no preference"),
            field=prefs.get("field", student_data.get("interests", "undecided")),
            budget=prefs.get("budget", "flexible"),
        )

        try:
            from ai_resilience import resilient_llm_call

            model = "claude-sonnet-4-20250514" if self._provider == "claude" else "gemini-2.0-flash"
            raw, _ = resilient_llm_call(self._provider, model, prompt)

            # Parse JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', raw)
            suggestions = {}
            if json_match:
                try:
                    suggestions = json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass

            return AgentResponse(
                content=raw,
                agent=self.AGENT_NAME,
                confidence=0.8,
                metadata={"suggestions": suggestions,
                          "predicted_total": student_data["predicted_total"]},
            )
        except Exception as e:
            return AgentResponse(
                content=f"Error suggesting universities: {str(e)}",
                agent=self.AGENT_NAME, confidence=0.0,
            )
