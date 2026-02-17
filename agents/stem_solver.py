"""STEM Solver Agent — Math/Physics/Chemistry computation with sandbox.

Uses GPT-4o to write Python code that solves problems, executes in a
restricted subprocess sandbox, and compares to student's answer.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap

from dotenv import load_dotenv

from agents.base import AgentResponse

load_dotenv()

# Whitelist of allowed modules in the sandbox
ALLOWED_MODULES = {"math", "numpy", "scipy", "statistics", "fractions", "decimal", "cmath"}

SANDBOX_TEMPLATE = textwrap.dedent("""\
import math
try:
    import numpy as np
except ImportError:
    np = None
try:
    import scipy
except ImportError:
    scipy = None

# Student code below
{code}
""")

STEM_SYSTEM = """You are an expert IB Mathematics/Physics/Chemistry problem solver.

When given a problem:
1. Write clean Python code that computes the answer
2. Use only: math, numpy, scipy, statistics, fractions, decimal
3. Print ONLY the final numerical answer (or a short result string)
4. Do NOT use file I/O, network, or subprocess calls
5. Keep the code concise — under 30 lines

Example output format:
```python
import math
result = math.sqrt(2) * 5
print(f"{{result:.4f}}")
```

IMPORTANT: Only output the Python code block, nothing else."""

GUIDANCE_SYSTEM = """You are a Socratic IB {subject} tutor helping a student with a calculation.

The correct answer is: {correct_answer}
The student's answer is: {student_answer}

If the student is correct (within reasonable rounding), congratulate them briefly.
If incorrect, guide them using the Socratic method:
1. Identify where their approach likely diverged
2. Ask a guiding question about the step they likely got wrong
3. Do NOT give the full solution — lead them to discover their error

Keep your response to 2-3 short paragraphs. Use markdown formatting."""


class STEMSolverAgent:
    """Solves STEM problems with verified computation."""

    AGENT_NAME = "stem_solver"

    def __init__(self) -> None:
        self._openai_client = None
        self._gemini_model = None
        self._provider = "none"
        self._init_provider()

    def _init_provider(self) -> None:
        """Initialize best available LLM provider for code generation."""
        # Try GPT-4o first (preferred for STEM)
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            try:
                import openai

                self._openai_client = openai.OpenAI(api_key=openai_key)
                self._provider = "openai"
                return
            except ImportError:
                pass

        # Fall back to Gemini
        google_key = os.getenv("GOOGLE_API_KEY")
        if google_key:
            try:
                import google.generativeai as genai

                genai.configure(api_key=google_key)
                self._gemini_model = genai.GenerativeModel("gemini-2.0-flash")
                self._provider = "gemini"
            except ImportError:
                pass

    def solve(
        self,
        question: str,
        student_work: str = "",
        subject: str = "Mathematics",
    ) -> AgentResponse:
        """Solve a STEM problem and compare to student's work."""
        if self._provider == "none":
            return AgentResponse(
                content="STEM solver requires an API key (OpenAI or Google).",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )

        # Step 1: Generate solver code
        code = self._generate_code(question, subject)
        if not code:
            return self._fallback_response(question, student_work, subject)

        # Step 2: Execute in sandbox
        result = self._execute_sandbox(code)
        if result is None:
            return self._fallback_response(question, student_work, subject)

        # Step 3: Generate Socratic guidance comparing answers
        guidance = self._generate_guidance(
            question, result, student_work, subject
        )

        return AgentResponse(
            content=guidance,
            agent=self.AGENT_NAME,
            confidence=0.85,
            metadata={
                "computed_answer": result,
                "code_used": code,
                "provider": self._provider,
            },
            follow_up="Would you like me to walk through the solution step by step?",
        )

    def _generate_code(self, question: str, subject: str) -> str | None:
        """Use LLM to generate Python code that solves the problem."""
        from ai_resilience import resilient_llm_call

        prompt = f"Subject: {subject}\nProblem: {question}\n\nWrite Python code to solve this."

        try:
            model = "gpt-4o" if self._provider == "openai" else "gemini-2.0-flash"
            raw, _ = resilient_llm_call(
                self._provider, model, prompt, system=STEM_SYSTEM,
            )
            return self._extract_code(raw)
        except Exception:
            return None

    def _extract_code(self, raw: str) -> str | None:
        """Extract Python code from LLM response."""
        # Look for code blocks
        if "```python" in raw:
            start = raw.index("```python") + len("```python")
            end = raw.index("```", start)
            return raw[start:end].strip()
        if "```" in raw:
            start = raw.index("```") + 3
            end = raw.index("```", start)
            return raw[start:end].strip()
        # If no code block, treat entire response as code
        lines = [l for l in raw.strip().splitlines() if not l.startswith("#")]
        if lines:
            return "\n".join(lines)
        return None

    def _execute_sandbox(self, code: str, timeout: int = 5) -> str | None:
        """Execute code in a restricted subprocess."""
        # Validate code safety
        forbidden = ["open(", "subprocess", "os.system", "exec(", "eval(",
                      "__import__", "importlib", "shutil", "pathlib",
                      "socket", "urllib", "requests", "http"]
        code_lower = code.lower()
        for token in forbidden:
            if token.lower() in code_lower:
                return None

        full_code = SANDBOX_TEMPLATE.format(code=code)

        try:
            result = subprocess.run(
                [sys.executable, "-c", full_code],
                capture_output=True,
                text=True,
                timeout=timeout,
                env={
                    "PATH": os.environ.get("PATH", ""),
                    "PYTHONPATH": "",
                },
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            return None
        except (subprocess.TimeoutExpired, Exception):
            return None

    def _generate_guidance(
        self,
        question: str,
        correct_answer: str,
        student_answer: str,
        subject: str,
    ) -> str:
        """Generate Socratic guidance comparing student's answer to computed answer."""
        from ai_resilience import resilient_llm_call

        system = GUIDANCE_SYSTEM.format(
            subject=subject,
            correct_answer=correct_answer,
            student_answer=student_answer or "Not provided",
        )
        prompt = f"Question: {question}\n\nHelp the student understand this problem."

        try:
            model = "gpt-4o" if self._provider == "openai" else "gemini-2.0-flash"
            text, _ = resilient_llm_call(
                self._provider, model, prompt, system=system,
            )
            return text
        except Exception:
            if student_answer:
                return (
                    f"The computed answer is **{correct_answer}**.\n\n"
                    f"Your answer: {student_answer}\n\n"
                    "Try reviewing your working step by step to find where the results diverge."
                )
            return f"The computed answer is **{correct_answer}**."

    def _fallback_response(
        self, question: str, student_work: str, subject: str
    ) -> AgentResponse:
        """Fallback when code generation or execution fails."""
        from ai_resilience import resilient_llm_call

        prompt = (
            f"Subject: {subject}\n"
            f"Question: {question}\n"
            f"Student's work: {student_work or 'None provided'}\n\n"
            "Guide the student through solving this step by step using the Socratic method."
        )

        try:
            model = "gpt-4o" if self._provider == "openai" else "gemini-2.0-flash"
            text, _ = resilient_llm_call(self._provider, model, prompt)

            return AgentResponse(
                content=text,
                agent=self.AGENT_NAME,
                confidence=0.6,
                metadata={"fallback": True, "provider": self._provider},
            )
        except Exception as e:
            return AgentResponse(
                content=f"I couldn't solve this problem automatically: {e}",
                agent=self.AGENT_NAME,
                confidence=0.0,
            )
