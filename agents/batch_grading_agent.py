"""Batch Grading Agent — Teacher Co-Pilot.

Processes multiple student submissions for a class assignment,
generating per-student grades and a class-wide summary.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime

from dotenv import load_dotenv

from agents.base import AgentResponse

load_dotenv()

BATCH_SYSTEM_PROMPT = """You are an IB examiner AI assistant helping a teacher grade student work.

For each student submission, provide:
1. Criterion-by-criterion marks (use the IB rubric for the subject/doc_type)
2. Overall grade (1-7 scale)
3. Key strengths (2-3 bullet points)
4. Areas for improvement (2-3 bullet points)
5. Any formatting or structural issues

Be consistent across all students. Use the same rubric standards.

Respond in JSON format:
{
    "mark_earned": <int>,
    "mark_total": <int>,
    "grade": <int 1-7>,
    "percentage": <int>,
    "criterion_scores": {"A": <int>, "B": <int>, ...},
    "strengths": ["...", "..."],
    "improvements": ["...", "..."],
    "formatting_issues": ["..."],
    "ai_text_risk": "low|medium|high",
    "ai_text_signals": ["..."]
}"""


class BatchGradingAgent:
    """Processes batch grading for teacher class assignments."""

    AGENT_NAME = "batch_grading_agent"

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

    def process_batch(
        self, submissions: list[dict], subject: str, doc_type: str = "ia",
    ) -> AgentResponse:
        """Grade a batch of student submissions.

        Each submission: {"student_id": int, "student_name": str, "text": str}
        """
        if self._provider == "none":
            return AgentResponse(
                content="Batch grading agent unavailable (no AI provider configured).",
                agent=self.AGENT_NAME, confidence=0.0,
            )

        results = []
        for sub in submissions:
            result = self._grade_single(sub, subject, doc_type)
            result["student_id"] = sub.get("student_id")
            result["student_name"] = sub.get("student_name", "Unknown")
            results.append(result)

        class_summary = self.generate_class_summary(results)

        return AgentResponse(
            content=json.dumps({"results": results, "class_summary": class_summary}),
            agent=self.AGENT_NAME,
            confidence=0.85,
            metadata={
                "results": results,
                "class_summary": class_summary,
                "total": len(submissions),
                "processed": len(results),
            },
        )

    def _grade_single(self, submission: dict, subject: str, doc_type: str) -> dict:
        """Grade a single submission."""
        text = submission.get("text", "")
        student_name = submission.get("student_name", "Student")

        prompt = (
            f"Grade this {doc_type.upper()} submission for {subject}.\n\n"
            f"Student: {student_name}\n\n"
            f"--- SUBMISSION ---\n{text[:5000]}\n--- END ---\n\n"
            "Provide your assessment in the JSON format specified."
        )

        try:
            from ai_resilience import resilient_llm_call

            model = "claude-sonnet-4-20250514" if self._provider == "claude" else "gemini-2.0-flash"
            raw, _ = resilient_llm_call(
                self._provider, model, prompt, system=BATCH_SYSTEM_PROMPT,
            )

            # Parse JSON response
            json_match = re.search(r'\{[\s\S]*\}', raw)
            if json_match:
                parsed = json.loads(json_match.group())
                # Add AI text detection
                ai_check = self.detect_ai_text(text)
                parsed["ai_text_risk"] = ai_check.get("risk_level", "low")
                parsed["ai_text_signals"] = ai_check.get("signals", [])
                return parsed
        except Exception:
            pass

        # Fallback result
        return {
            "mark_earned": 0, "mark_total": 0, "grade": 0, "percentage": 0,
            "criterion_scores": {}, "strengths": [], "improvements": [],
            "formatting_issues": ["Grading failed — manual review needed"],
            "ai_text_risk": "unknown", "ai_text_signals": [],
        }

    def generate_class_summary(self, results: list[dict]) -> dict:
        """Aggregate per-student results into a class-wide summary."""
        if not results:
            return {"grade_distribution": {}, "avg_grade": 0, "common_issues": [],
                    "weakest_criteria": [], "outliers": {"best": [], "worst": []}}

        grades = [r.get("grade", 0) for r in results if r.get("grade", 0) > 0]
        distribution = {}
        for g in grades:
            distribution[str(g)] = distribution.get(str(g), 0) + 1

        avg_grade = sum(grades) / len(grades) if grades else 0

        # Collect all improvements across students
        all_improvements = []
        for r in results:
            all_improvements.extend(r.get("improvements", []))

        # Count common issues
        issue_counts: dict[str, int] = {}
        for issue in all_improvements:
            key = issue.lower().strip()[:50]
            issue_counts[key] = issue_counts.get(key, 0) + 1
        common_issues = sorted(issue_counts.items(), key=lambda x: -x[1])[:5]

        # Collect criterion scores
        criteria_totals: dict[str, list[int]] = {}
        for r in results:
            for crit, score in r.get("criterion_scores", {}).items():
                if crit not in criteria_totals:
                    criteria_totals[crit] = []
                criteria_totals[crit].append(score)

        weakest = []
        for crit, scores in criteria_totals.items():
            avg = sum(scores) / len(scores) if scores else 0
            weakest.append({"criterion": crit, "avg_score": round(avg, 1)})
        weakest.sort(key=lambda x: x["avg_score"])

        # Outliers
        sorted_results = sorted(results, key=lambda x: x.get("grade", 0))
        best = [{"name": r["student_name"], "grade": r.get("grade", 0)}
                for r in sorted_results[-3:] if r.get("grade", 0) > 0]
        worst = [{"name": r["student_name"], "grade": r.get("grade", 0)}
                 for r in sorted_results[:3] if r.get("grade", 0) > 0]

        # AI text risk summary
        high_risk = [r["student_name"] for r in results
                     if r.get("ai_text_risk") == "high"]

        return {
            "grade_distribution": distribution,
            "avg_grade": round(avg_grade, 1),
            "common_issues": [{"issue": i, "count": c} for i, c in common_issues],
            "weakest_criteria": weakest[:3],
            "outliers": {"best": best, "worst": worst},
            "ai_text_flags": high_risk,
            "total_graded": len(grades),
        }

    def detect_ai_text(self, text: str) -> dict:
        """Heuristic AI-generated text detection.

        Checks: vocabulary uniformity, paragraph structure, hedging patterns.
        """
        signals = []
        words = text.split()
        word_count = len(words)

        if word_count < 50:
            return {"risk_level": "low", "signals": []}

        # Check for overly uniform paragraph lengths
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if len(paragraphs) >= 3:
            lengths = [len(p.split()) for p in paragraphs]
            avg_len = sum(lengths) / len(lengths)
            if avg_len > 0:
                variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
                cv = (variance ** 0.5) / avg_len
                if cv < 0.15:
                    signals.append("Unusually uniform paragraph lengths")

        # Check for hedging/qualifier patterns (common in AI text)
        hedging = ["it is important to note", "it should be noted",
                    "furthermore", "moreover", "in conclusion",
                    "it is worth mentioning", "on the other hand"]
        hedging_count = sum(1 for h in hedging if h in text.lower())
        if hedging_count >= 4:
            signals.append("High frequency of hedging/transition phrases")

        # Check for overly formal connectives
        formal = ["consequently", "subsequently", "notwithstanding",
                   "henceforth", "aforementioned"]
        formal_count = sum(1 for f in formal if f in text.lower())
        if formal_count >= 3:
            signals.append("Unusually formal connective usage")

        # Determine risk level
        if len(signals) >= 2:
            risk = "high"
        elif len(signals) == 1:
            risk = "medium"
        else:
            risk = "low"

        return {"risk_level": risk, "signals": signals}
