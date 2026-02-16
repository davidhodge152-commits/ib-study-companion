"""
The Mirror — IB Examiner Grading Engine

Sends student answers + retrieved mark scheme context to Gemini,
using a strict IB Examiner persona that grades on a 1-7 scale and
cites specific rubric points when deducting marks.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag_engine import RAGEngine

from subject_config import get_subject_config, SubjectConfig

SESSION_DIR = Path(__file__).parent / "session_data"
SESSION_DIR.mkdir(exist_ok=True)

IB_EXAMINER_SYSTEM_PROMPT = """You are a SENIOR IB EXAMINER with 15+ years of experience marking
IB Diploma Programme papers. You are precise, fair, but strict.

YOUR GRADING PROTOCOL:

1. IDENTIFY the command term in the question. Each command term has a specific
   expectation:
   - "Define" / "State" / "List" → factual recall only, 1-2 marks
   - "Describe" / "Outline" → characteristics + some detail, 2-4 marks
   - "Explain" → cause/mechanism with reasoning, 3-6 marks
   - "Analyse" → break down components, show relationships, 6-8 marks
   - "Evaluate" / "Discuss" / "To what extent" → balanced argument with
     judgement, weighing evidence on BOTH sides, 8-15 marks
   - "Compare and contrast" → explicit similarities AND differences

2. APPLY the mark scheme criteria. For each mark point the student earns,
   state which criterion it satisfies. For each mark point missed, explain
   EXACTLY what was required.

3. CHECK for common IB penalties:
   - Vague language ("it affects things") → deduct for lack of specificity
   - Missing key terminology → note which terms were expected
   - One-sided evaluation (no counter-argument) → cap at 50% for evaluative Qs
   - No real-world examples when expected → note the omission
   - Exceeding word limits or not answering the actual question asked

4. ASSIGN a final mark out of the question's total AND convert to a 1-7 grade
   using these approximate bands:
   - 7: 80-100%  (Excellent — comprehensive, well-structured, insightful)
   - 6: 70-79%   (Very good — thorough with minor gaps)
   - 5: 60-69%   (Good — solid understanding, some gaps)
   - 4: 50-59%   (Satisfactory — basic understanding demonstrated)
   - 3: 40-49%   (Mediocre — significant gaps, partial understanding)
   - 2: 25-39%   (Poor — limited relevant content)
   - 1: 0-24%    (Very poor — little to no relevant content)

5. PROVIDE structured feedback:
   - STRENGTHS: What the student did well (be specific)
   - IMPROVEMENTS: What was missing or incorrect (cite rubric points)
   - EXAMINER TIP: One actionable piece of advice for next time

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
[Write a concise model answer that would earn full marks on this question. Use bullet points where appropriate. This helps the student understand what an ideal response looks like.]"""


@dataclass
class GradeResult:
    question: str
    answer: str
    mark_earned: int
    mark_total: int
    grade: int  # 1-7
    percentage: int
    strengths: list[str]
    improvements: list[str]
    examiner_tip: str
    full_commentary: str
    raw_response: str
    model_answer: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class IBGrader:
    """Grades student answers using the IB Examiner persona."""

    def __init__(self, engine: RAGEngine, user_id: int = 1) -> None:
        self.engine = engine
        self.user_id = user_id
        self._history_db = None

    @property
    def _db(self):
        if self._history_db is None:
            from db_stores import GradeHistoryDB
            self._history_db = GradeHistoryDB(self.user_id)
        return self._history_db

    @property
    def history(self) -> list[GradeResult]:
        """Load history from DB on demand."""
        results = []
        for entry in self._db.history:
            results.append(GradeResult(
                question=entry["question"],
                answer=entry.get("answer", ""),
                mark_earned=entry["mark_earned"],
                mark_total=entry["mark_total"],
                grade=entry["grade"],
                percentage=entry["percentage"],
                strengths=entry["strengths"],
                improvements=entry["improvements"],
                examiner_tip=entry["examiner_tip"],
                full_commentary=entry.get("full_commentary", ""),
                raw_response=entry.get("raw_response", ""),
                model_answer=entry.get("model_answer", ""),
                timestamp=entry.get("timestamp", ""),
            ))
        return results

    def grade(
        self,
        question: str,
        answer: str,
        subject: str,
        marks: int,
        command_term: str = "",
        subject_display: str = "",
    ) -> GradeResult:
        """Grade a student's answer against mark scheme context."""
        # Retrieve relevant mark scheme criteria (if documents exist)
        mark_chunks = []
        guide_chunks = []
        try:
            mark_chunks = self.engine.query(
                query_text=f"{subject} {command_term} mark scheme {question[:100]}",
                n_results=5,
                doc_type="mark_scheme",
            )
            guide_chunks = self.engine.query(
                query_text=f"{subject} syllabus {question[:80]}",
                n_results=3,
                doc_type="subject_guide",
            )
        except (FileNotFoundError, Exception):
            pass

        context_marks = "\n---\n".join(c.text for c in mark_chunks) or "No mark scheme available — use general IB marking criteria."
        context_guide = "\n---\n".join(c.text for c in guide_chunks) or ""

        # Build subject-specific grading context
        subject_context = ""
        config = get_subject_config(subject_display or subject.replace("_", " ").title())
        if config:
            ct_note = ""
            if command_term and command_term in config.key_command_terms:
                ct_note = f"\nCOMMAND TERM NOTE FOR THIS SUBJECT: {config.key_command_terms[command_term]}"

            pitfalls = "\n".join(f"  - {p}" for p in config.common_pitfalls)
            subject_context = f"""
SUBJECT-SPECIFIC GRADING INTELLIGENCE:
Category: {config.category}
{ct_note}

COMMON PITFALLS TO CHECK FOR:
{pitfalls}

GRADE BOUNDARIES (approximate):
  Grade 7: {config.grade_boundaries_hl.get(7, 80)}%+ | Grade 6: {config.grade_boundaries_hl.get(6, 70)}%+
  Grade 5: {config.grade_boundaries_hl.get(5, 60)}%+ | Grade 4: {config.grade_boundaries_hl.get(4, 50)}%+
"""

        grading_prompt = f"""MARK SCHEME CONTEXT:
{context_marks}

SYLLABUS CONTEXT:
{context_guide}
{subject_context}
QUESTION ({marks} marks):
{question}

COMMAND TERM: {command_term or 'Not specified'}

STUDENT ANSWER:
{answer}

Grade this answer according to your protocol. The question is worth {marks} marks."""

        raw = self.engine.ask(grading_prompt, system=IB_EXAMINER_SYSTEM_PROMPT)

        result = self._parse_grade(question, answer, marks, raw)
        self._db.append(result)

        # Update adaptive difficulty engine
        try:
            from adaptive import estimate_difficulty, update_theta
            diff = estimate_difficulty(marks, command_term)
            correct_ratio = result.mark_earned / result.mark_total if result.mark_total > 0 else 0
            update_theta(self.user_id, subject, subject_display or subject, diff, correct_ratio)
        except Exception:
            pass  # Adaptive engine is optional

        return result

    def get_analytics(self) -> dict:
        """Return analytics across all graded answers."""
        if not self.history:
            return {
                "total_answers": 0,
                "average_grade": 0.0,
                "average_percentage": 0.0,
                "grade_distribution": {},
                "trend": [],
            }

        grades = [r.grade for r in self.history]
        percentages = [r.percentage for r in self.history]
        dist = {g: grades.count(g) for g in range(1, 8) if grades.count(g) > 0}

        # Trend: moving average over last 10
        window = min(10, len(percentages))
        trend = []
        for i in range(len(percentages)):
            start = max(0, i - window + 1)
            avg = sum(percentages[start : i + 1]) / (i - start + 1)
            trend.append(round(avg, 1))

        return {
            "total_answers": len(self.history),
            "average_grade": round(sum(grades) / len(grades), 2),
            "average_percentage": round(sum(percentages) / len(percentages), 1),
            "grade_distribution": dist,
            "trend": trend,
        }

    def get_weakness_report(self) -> str:
        """Analyze all improvements across history to find patterns."""
        if len(self.history) < 3:
            return "Need at least 3 graded answers to generate a weakness report."

        all_improvements = []
        for r in self.history[-20:]:
            all_improvements.extend(r.improvements)

        prompt = f"""Analyze these examiner improvement notes from a student's recent IB answers
and identify the TOP 3 recurring weaknesses / bad habits:

{chr(10).join('- ' + imp for imp in all_improvements)}

For each weakness:
1. Name the pattern
2. Explain why it costs marks
3. Give a specific fix the student can practice

Be concise and actionable."""

        return self.engine.ask(prompt)

    # ── Parsing ────────────────────────────────────────────────────

    def _parse_grade(
        self, question: str, answer: str, total_marks: int, raw: str
    ) -> GradeResult:
        lines = raw.splitlines()
        mark_earned = 0
        grade = 4
        percentage = 50
        strengths: list[str] = []
        improvements: list[str] = []
        examiner_tip = ""
        full_commentary = ""
        model_answer = ""

        section = ""
        for line in lines:
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

        return GradeResult(
            question=question,
            answer=answer,
            mark_earned=mark_earned,
            mark_total=total_marks,
            grade=grade,
            percentage=percentage,
            strengths=strengths,
            improvements=improvements,
            model_answer=model_answer.strip(),
            examiner_tip=examiner_tip.strip(),
            full_commentary=full_commentary.strip(),
            raw_response=raw,
        )

