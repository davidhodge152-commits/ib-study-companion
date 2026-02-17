"""Vision Agent — ECF & Handwriting Autopsy.

Analyzes photos of student handwritten work step-by-step, identifies
the first error point, and awards Error Carried Forward (ECF) marks
for subsequent steps where the student used their wrong value correctly.

Uses Gemini Vision for handwriting extraction and the STEM sandbox
for computational verification.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from typing import TYPE_CHECKING

from dotenv import load_dotenv

from agents.base import AgentResponse

if TYPE_CHECKING:
    pass

load_dotenv()

EXTRACTION_PROMPT = """Extract each line of mathematical/scientific working from this handwritten image.

Return a JSON array of objects, each representing one line of working:
[
  {"line_num": 1, "expression": "F = ma", "result": "F = 2 * 9.81", "description": "Applied Newton's second law"},
  {"line_num": 2, "expression": "F = 19.62 N", "result": "19.62", "description": "Calculated force"}
]

RULES:
- Extract EVERY line of working, including intermediate steps
- For each line, give the mathematical expression the student wrote
- Give the numerical result if one was computed
- Describe what the student was doing in that step
- If a line is unclear, mark it with "unclear": true
- Return ONLY the JSON array, no other text"""

ECF_ANALYSIS_PROMPT = """You are an IB examiner analyzing a student's mathematical/scientific working.

QUESTION: {question}
SUBJECT: {subject}
TOTAL MARKS: {marks}
COMMAND TERM: {command_term}

STUDENT'S EXTRACTED WORKING:
{student_steps}

CORRECT WORKING (computed):
{correct_steps}

Analyze the student's work step by step and apply IB ECF (Error Carried Forward) marking:

MARKING RULES:
1. Award "A" (Accuracy) marks for correct answers/values
2. Award "M" (Method) marks for correct method even if the value is wrong
3. Award "ECF" marks when the student makes an error but then correctly applies
   their wrong value in subsequent steps (Error Carried Forward)
4. Award "0" for incorrect method AND incorrect value

FORMAT your response EXACTLY as:
ERROR_LINE: [line number where first error occurred, or "none"]
LINE_ANALYSIS:
Line 1: [M|A|ECF|0] - [brief explanation]
Line 2: [M|A|ECF|0] - [brief explanation]
...
TOTAL_EARNED: [marks earned] / {marks}
ECF_MARKS: [number of ECF marks awarded]
SUMMARY: [2-3 sentence explanation of where the student went wrong and what they got right via ECF]
ADVICE: [specific advice on how to avoid this error]"""

SOLVER_CODE_PROMPT = """Write Python code to solve this problem step by step.
Print each step as a JSON object on a separate line.

Subject: {subject}
Question: {question}

Format each step as:
print('{{"step": 1, "expression": "F = ma", "result": "19.62", "description": "Applied Newton\'s second law"}}')

IMPORTANT:
- Show ALL intermediate calculation steps
- Use only: math, numpy, scipy
- Print each step as a separate JSON line
- The last line should be the final answer"""


class VisionAgent:
    """Analyzes handwritten work with ECF marking."""

    AGENT_NAME = "vision_agent"

    def __init__(self) -> None:
        self._gemini_model = None
        self._gemini_vision = None
        self._provider = "none"
        self._init_provider()

    def _init_provider(self) -> None:
        """Initialize Gemini Vision for handwriting extraction."""
        google_key = os.getenv("GOOGLE_API_KEY")
        if google_key:
            try:
                import google.generativeai as genai

                genai.configure(api_key=google_key)
                self._gemini_vision = genai.GenerativeModel("gemini-2.0-flash")
                self._gemini_model = genai.GenerativeModel("gemini-2.0-flash")
                self._provider = "gemini"
            except ImportError:
                pass

    def analyze_handwriting(
        self,
        image_data: bytes,
        question: str,
        subject: str,
        marks: int = 4,
        command_term: str = "",
        user_id: int | None = None,
    ) -> AgentResponse:
        """Analyze handwritten work with ECF marking."""
        if self._provider == "none":
            return AgentResponse(
                content="Vision agent requires a Google API key for Gemini Vision.",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

        # Step 1: Extract handwritten steps via vision
        student_steps = self._extract_steps(image_data)
        if not student_steps:
            return AgentResponse(
                content="I couldn't extract any working from the image. "
                "Please ensure the handwriting is clear and well-lit.",
                agent=self.AGENT_NAME,
                confidence=0.2,
                metadata={"error": "extraction_failed"},
            )

        # Step 2: Compute correct solution via STEM sandbox
        correct_steps = self._compute_correct(question, subject)

        # Step 3: Perform ECF analysis
        ecf_result = self._compute_ecf(
            student_steps, correct_steps, question, subject, marks, command_term
        )

        # Step 4: Save analysis to database
        if user_id:
            self._save_analysis(
                user_id, subject, question, image_data,
                student_steps, ecf_result, marks
            )

        # Format response
        content = self._format_response(
            student_steps, ecf_result, marks, subject
        )

        return AgentResponse(
            content=content,
            agent=self.AGENT_NAME,
            confidence=0.8,
            metadata={
                "total_marks": marks,
                "earned_marks": ecf_result.get("earned_marks", 0),
                "ecf_marks": ecf_result.get("ecf_marks", 0),
                "error_line": ecf_result.get("error_line"),
                "steps_extracted": len(student_steps),
                "line_analysis": ecf_result.get("line_analysis", []),
            },
            follow_up="Would you like me to show you the correct working step by step?",
        )

    def extract_text(self, image_data: bytes) -> AgentResponse:
        """Extract text from an image using Gemini Vision (general OCR)."""
        if self._provider == "none":
            return AgentResponse(
                content="",
                agent=self.AGENT_NAME,
                confidence=0.0,
                metadata={"error": "no_provider"},
            )
        try:
            image_part = {"mime_type": "image/jpeg", "data": image_data}
            response = self._gemini_vision.generate_content(
                [
                    "Extract ALL text from this image. Return the text exactly as written, "
                    "preserving any mathematical notation, formatting, and line breaks. "
                    "If there are equations, use standard mathematical notation.",
                    image_part,
                ]
            )
            return AgentResponse(
                content=response.text.strip(),
                agent=self.AGENT_NAME,
                confidence=0.8,
            )
        except Exception as e:
            return AgentResponse(
                content="",
                agent=self.AGENT_NAME,
                confidence=0.0,
                metadata={"error": str(e)},
            )

    def _extract_steps(self, image_data: bytes) -> list[dict]:
        """Extract handwritten working steps via Gemini Vision."""
        try:
            import google.generativeai as genai

            image_part = {"mime_type": "image/jpeg", "data": image_data}
            response = self._gemini_vision.generate_content(
                [EXTRACTION_PROMPT, image_part]
            )
            raw = response.text.strip()

            # Parse JSON from response
            if "```" in raw:
                start = raw.index("[")
                end = raw.rindex("]") + 1
                raw = raw[start:end]
            elif raw.startswith("["):
                pass
            else:
                start = raw.index("[")
                end = raw.rindex("]") + 1
                raw = raw[start:end]

            steps = json.loads(raw)
            return steps if isinstance(steps, list) else []
        except Exception:
            return []

    def _compute_correct(self, question: str, subject: str) -> list[dict]:
        """Compute the correct solution step by step using STEM sandbox."""
        try:
            from agents.stem_solver import STEMSolverAgent

            solver = STEMSolverAgent()
            prompt = SOLVER_CODE_PROMPT.format(subject=subject, question=question)

            code = solver._generate_code(
                f"Solve step by step and print each step as JSON: {question}",
                subject,
            )
            if not code:
                return []

            result = solver._execute_sandbox(code)
            if not result:
                return []

            steps = []
            for line in result.strip().splitlines():
                try:
                    step = json.loads(line)
                    steps.append(step)
                except (json.JSONDecodeError, ValueError):
                    continue
            return steps
        except Exception:
            return []

    def _compute_ecf(
        self,
        student_steps: list[dict],
        correct_steps: list[dict],
        question: str,
        subject: str,
        marks: int,
        command_term: str,
    ) -> dict:
        """Perform ECF analysis using LLM comparison."""
        student_text = json.dumps(student_steps, indent=2)
        correct_text = json.dumps(correct_steps, indent=2) if correct_steps else "Not available"

        prompt = ECF_ANALYSIS_PROMPT.format(
            question=question,
            subject=subject,
            marks=marks,
            command_term=command_term or "Calculate",
            student_steps=student_text,
            correct_steps=correct_text,
        )

        try:
            response = self._gemini_model.generate_content(prompt)
            raw = response.text.strip()
            return self._parse_ecf_response(raw, marks)
        except Exception:
            return {
                "earned_marks": 0,
                "ecf_marks": 0,
                "error_line": None,
                "line_analysis": [],
                "summary": "Could not complete ECF analysis.",
                "advice": "",
            }

    def _parse_ecf_response(self, raw: str, total_marks: int) -> dict:
        """Parse structured ECF analysis response."""
        result = {
            "earned_marks": 0,
            "ecf_marks": 0,
            "error_line": None,
            "line_analysis": [],
            "summary": "",
            "advice": "",
        }

        lines = raw.splitlines()
        in_line_analysis = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("ERROR_LINE:"):
                val = stripped.split(":", 1)[1].strip()
                result["error_line"] = int(val) if val.isdigit() else None
            elif stripped.startswith("TOTAL_EARNED:"):
                try:
                    earned = stripped.split(":", 1)[1].strip().split("/")[0].strip()
                    result["earned_marks"] = int(earned)
                except (ValueError, IndexError):
                    pass
            elif stripped.startswith("ECF_MARKS:"):
                try:
                    result["ecf_marks"] = int(stripped.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif stripped.startswith("SUMMARY:"):
                result["summary"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("ADVICE:"):
                result["advice"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("LINE_ANALYSIS:"):
                in_line_analysis = True
            elif in_line_analysis and stripped.startswith("Line "):
                result["line_analysis"].append(stripped)

        return result

    def _format_response(
        self,
        student_steps: list[dict],
        ecf_result: dict,
        marks: int,
        subject: str,
    ) -> str:
        """Format the ECF analysis into a readable response."""
        parts = [f"## Handwriting Analysis — {subject}\n"]

        # Extracted working
        parts.append("### Your Working (Extracted)")
        for step in student_steps:
            line_num = step.get("line_num", "?")
            expr = step.get("expression", "")
            desc = step.get("description", "")
            parts.append(f"**Line {line_num}:** `{expr}` — {desc}")

        parts.append("")

        # ECF breakdown
        earned = ecf_result.get("earned_marks", 0)
        ecf = ecf_result.get("ecf_marks", 0)
        error_line = ecf_result.get("error_line")

        parts.append(f"### Mark Breakdown: **{earned}/{marks}**")
        if ecf > 0:
            parts.append(f"*Including {ecf} ECF mark{'s' if ecf != 1 else ''}*\n")

        if error_line:
            parts.append(f"First error at **Line {error_line}**\n")

        # Line-by-line analysis
        for analysis in ecf_result.get("line_analysis", []):
            parts.append(f"- {analysis}")

        parts.append("")

        # Summary and advice
        if ecf_result.get("summary"):
            parts.append(f"### Summary\n{ecf_result['summary']}\n")
        if ecf_result.get("advice"):
            parts.append(f"### How to Improve\n{ecf_result['advice']}")

        return "\n".join(parts)

    def _save_analysis(
        self,
        user_id: int,
        subject: str,
        question: str,
        image_data: bytes,
        steps: list[dict],
        ecf_result: dict,
        marks: int,
    ) -> None:
        """Persist analysis to the handwriting_analyses table."""
        try:
            from database import get_db

            db = get_db()
            image_hash = hashlib.sha256(image_data).hexdigest()[:16]
            db.execute(
                "INSERT INTO handwriting_analyses "
                "(user_id, subject, question, image_hash, extracted_steps, "
                "ecf_breakdown, total_marks, earned_marks, ecf_marks, "
                "error_line, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    user_id,
                    subject,
                    question,
                    image_hash,
                    json.dumps(steps),
                    json.dumps(ecf_result),
                    marks,
                    ecf_result.get("earned_marks", 0),
                    ecf_result.get("ecf_marks", 0),
                    ecf_result.get("error_line"),
                    datetime.now().isoformat(),
                ),
            )
            db.commit()
        except Exception:
            pass
