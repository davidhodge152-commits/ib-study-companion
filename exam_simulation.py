"""
Real Exam Paper Simulation — Full IB paper generator with timing and grading.
"""

from __future__ import annotations

from subject_config import get_subject_config


class ExamPaperGenerator:
    """Generates realistic full IB exam papers using Gemini."""

    def __init__(self, engine) -> None:
        self.engine = engine

    def generate_paper(self, subject: str, level: str = "HL",
                       paper_number: int = 1) -> dict:
        """Generate a complete exam paper with section structure.

        Returns dict with: questions, duration_minutes, total_marks, sections.
        """
        config = get_subject_config(subject)

        # Determine paper parameters from config
        duration = 90  # default
        total_marks = 60
        if config:
            components = config.assessment_hl if level == "HL" else config.assessment_sl
            for comp in components:
                if f"Paper {paper_number}" in comp.name:
                    duration = comp.duration_minutes
                    total_marks = comp.marks
                    break

        if not self.engine or not self.engine.model:
            raise RuntimeError("AI engine is not configured — check GOOGLE_API_KEY")

        display_subject = subject.replace("_", " ").title()

        prompt = f"""You are an IB {display_subject} ({level}) Chief Examiner creating Paper {paper_number}.

Generate a COMPLETE exam paper with the following specifications:
- Subject: {display_subject}
- Level: {level}
- Paper: {paper_number}
- Duration: {duration} minutes
- Total marks: {total_marks}

REQUIREMENTS:
1. Structure the paper into sections (Section A: short answer, Section B: extended response)
2. Each question must have: question text, marks allocation, command term
3. Mark allocations must sum to {total_marks}
4. Use appropriate IB command terms
5. Questions must be answerable in text only (no diagrams/graphs required)
6. Include sub-parts where appropriate (a, b, c)

FORMAT each question as:
SECTION: [A or B]
QUESTION_NUMBER: [number]
QUESTION: [full question text]
MARKS: [integer]
COMMAND_TERM: [the IB command term]
---"""

        response = self.engine.model.generate_content(prompt)
        text = response.text

        questions = []
        current_section = "A"
        blocks = text.split("---")

        for block in blocks:
            block = block.strip()
            if not block or "QUESTION:" not in block:
                continue

            q = {}
            for line in block.splitlines():
                line = line.strip()
                if line.startswith("SECTION:"):
                    current_section = line.split(":", 1)[1].strip()
                elif line.startswith("QUESTION_NUMBER:"):
                    q["number"] = line.split(":", 1)[1].strip()
                elif line.startswith("QUESTION:"):
                    q["question"] = line.split(":", 1)[1].strip()
                elif line.startswith("MARKS:"):
                    try:
                        q["marks"] = int("".join(c for c in line.split(":", 1)[1] if c.isdigit()))
                    except (ValueError, IndexError):
                        q["marks"] = 4
                elif line.startswith("COMMAND_TERM:"):
                    q["command_term"] = line.split(":", 1)[1].strip()

            if "question" in q and len(q["question"].split()) >= 5:
                # Normalise keys for the frontend
                q["question_text"] = q.pop("question")
                q.setdefault("section", current_section)
                q.setdefault("marks", 4)
                q.setdefault("command_term", "")
                q.setdefault("number", str(len(questions) + 1))
                try:
                    q["number"] = int(q["number"])
                except (ValueError, TypeError):
                    q["number"] = len(questions) + 1
                questions.append(q)

        return {
            "subject": subject,
            "level": level,
            "paper_number": paper_number,
            "duration_minutes": duration,
            "total_marks": total_marks,
            "reading_time_minutes": 5,
            "questions": questions,
        }

    @staticmethod
    def calculate_grade(subject: str, level: str, total_marks: int,
                        earned_marks: int) -> int:
        """Calculate IB grade (1-7) from marks using grade boundaries."""
        if total_marks <= 0:
            return 1
        percentage = (earned_marks / total_marks) * 100

        config = get_subject_config(subject)
        if config:
            boundaries = config.grade_boundaries_hl if level == "HL" else config.grade_boundaries_sl
            if boundaries:
                for grade in range(7, 0, -1):
                    if percentage >= boundaries.get(grade, 0):
                        return grade
                return 1

        # Default boundaries
        if percentage >= 80: return 7
        elif percentage >= 70: return 6
        elif percentage >= 60: return 5
        elif percentage >= 50: return 4
        elif percentage >= 40: return 3
        elif percentage >= 25: return 2
        return 1
