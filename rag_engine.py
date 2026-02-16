"""
The Strategist — RAG Retrieval + Google Search Grounding

Provides a decoupled interface for:
  1. Querying the local ChromaDB knowledge base (past papers, mark schemes, notes).
  2. Fetching live grade boundaries via Gemini search grounding.
  3. Generating new exam-style questions from retrieved context.

This module has ZERO UI dependencies so it can be reused from a web API.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import google.generativeai as genai
from dotenv import load_dotenv

from subject_config import get_subject_config, get_syllabus_topics, SubjectConfig

load_dotenv()

CHROMA_DIR = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "ib_documents"


@dataclass
class RetrievedChunk:
    text: str
    source: str
    doc_type: str
    subject: str
    level: str
    distance: float


@dataclass
class GradeBoundary:
    subject: str
    level: str
    session: str
    boundaries: dict[int, int]  # grade -> min marks
    raw_text: str


@dataclass
class GeneratedQuestion:
    question_text: str
    command_term: str
    marks: int
    topic: str
    source_context: str  # the chunk that inspired it
    model_answer: str = ""


class RAGEngine:
    """Decoupled retrieval engine — no UI imports."""

    def __init__(self) -> None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GOOGLE_API_KEY not set. Copy .env.example to .env and add your key."
            )
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")
        self._chroma_client = None
        self._collection = None

    # ── ChromaDB access ────────────────────────────────────────────

    def _get_collection(self):
        """Lazily initialise ChromaDB collection on first access."""
        if self._collection is None:
            if not CHROMA_DIR.exists():
                raise FileNotFoundError(
                    f"No ChromaDB store at {CHROMA_DIR}. Run `python ingest.py` first."
                )
            import chromadb
            self._chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
            self._collection = self._chroma_client.get_collection(COLLECTION_NAME)
        return self._collection

    @property
    def collection(self):
        return self._get_collection()

    def collection_stats(self) -> dict:
        """Return summary stats about ingested documents."""
        try:
            col = self.collection
        except Exception:
            return {"count": 0, "subjects": [], "doc_types": []}

        data = col.get(include=["metadatas"])
        subjects = sorted({m.get("subject", "unknown") for m in data["metadatas"]})
        doc_types = sorted({m.get("doc_type", "unknown") for m in data["metadatas"]})
        sources = sorted({m.get("source", "unknown") for m in data["metadatas"]})
        return {
            "count": col.count(),
            "subjects": subjects,
            "doc_types": doc_types,
            "sources": sources,
        }

    # ── Retrieval ──────────────────────────────────────────────────

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        subject: Optional[str] = None,
        doc_type: Optional[str] = None,
        level: Optional[str] = None,
    ) -> list[RetrievedChunk]:
        """Retrieve the most relevant chunks from the vector store."""
        where_filter: dict | None = None
        conditions = []
        if subject:
            conditions.append({"subject": subject})
        if doc_type:
            conditions.append({"doc_type": doc_type})
        if level:
            conditions.append({"level": level})

        if len(conditions) == 1:
            where_filter = conditions[0]
        elif len(conditions) > 1:
            where_filter = {"$and": conditions}

        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        chunks: list[RetrievedChunk] = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            chunks.append(
                RetrievedChunk(
                    text=doc,
                    source=meta.get("source", ""),
                    doc_type=meta.get("doc_type", ""),
                    subject=meta.get("subject", ""),
                    level=meta.get("level", ""),
                    distance=dist,
                )
            )
        return chunks

    # ── Question generation ────────────────────────────────────────

    def generate_questions(
        self,
        subject: str,
        topic: str,
        level: str = "HL",
        count: int = 3,
        style: str = "mixed",
        subject_config: SubjectConfig | None = None,
        difficulty_level: int = 0,
    ) -> list[GeneratedQuestion]:
        """
        Generate new exam-style questions by first retrieving past paper
        context, then prompting Gemini to create novel questions in the
        same style. If subject_config is provided, injects subject-specific
        command term guidance and assessment format into the prompt.
        """
        # Auto-lookup config if not passed
        if subject_config is None:
            subject_config = get_subject_config(subject.replace("_", " ").title())

        # Pull relevant past paper questions as style exemplars (if documents exist)
        past_paper_chunks: list[RetrievedChunk] = []
        mark_scheme_chunks: list[RetrievedChunk] = []
        try:
            past_paper_chunks = self.query(
                query_text=f"{subject} {topic} exam question",
                n_results=6,
                subject=subject if subject != "any" else None,
                doc_type="past_paper",
                level=level if level != "unknown" else None,
            )
            mark_scheme_chunks = self.query(
                query_text=f"{subject} {topic} mark scheme criteria",
                n_results=4,
                subject=subject if subject != "any" else None,
                doc_type="mark_scheme",
                level=level if level != "unknown" else None,
            )
        except (FileNotFoundError, Exception):
            # No documents ingested yet — generate questions from subject intelligence alone
            pass

        context_papers = "\n---\n".join(c.text for c in past_paper_chunks) or "No past papers available — use your knowledge of IB exam style."
        context_marks = "\n---\n".join(c.text for c in mark_scheme_chunks) or "No mark schemes available — use standard IB marking criteria."

        # Build syllabus context — ground questions in real IB content
        syllabus_context = ""
        display_subject = subject.replace("_", " ").title()
        syllabus_topics = get_syllabus_topics(display_subject)
        if syllabus_topics:
            # Find matching topic and its subtopics
            matched_subtopics = []
            for st in syllabus_topics:
                if topic.lower() in st.name.lower() or st.name.lower() in topic.lower():
                    matched_subtopics = st.subtopics
                    break
            if not matched_subtopics:
                # No exact match — include all subtopics from all topics for context
                matched_subtopics = []
                for st in syllabus_topics:
                    if not st.hl_only or level == "HL":
                        matched_subtopics.extend(st.subtopics[:3])
            syllabus_context = f"""
IB SYLLABUS CONTENT FOR "{topic}" ({display_subject} {level}):
The following are the ACTUAL IB syllabus subtopics that students study. Your questions MUST test knowledge from this list:
{chr(10).join('  - ' + s for s in matched_subtopics)}

IMPORTANT: Generate questions that test these specific syllabus points. Do NOT invent content outside the IB {display_subject} syllabus.
"""

        # Build subject-specific guidance
        subject_guidance = ""
        if subject_config:
            ct_notes = "\n".join(
                f"  - {term}: {note}"
                for term, note in subject_config.key_command_terms.items()
            )
            subject_guidance = f"""
SUBJECT-SPECIFIC COMMAND TERM GUIDANCE:
{ct_notes}

COMMON PITFALLS TO TEST (design questions that probe these weaknesses):
{chr(10).join('  - ' + p for p in subject_config.common_pitfalls[:3])}
"""

        # Build adaptive difficulty guidance
        difficulty_guidance = ""
        if difficulty_level >= 1:
            difficulty_map = {
                1: ("Define, State, List, Describe", "1-4", "recall and definitions"),
                2: ("Describe, Outline, Identify, Annotate", "2-4", "descriptions and outlines"),
                3: ("Explain, Outline, Suggest", "3-6", "explanations with cause-effect reasoning"),
                4: ("Analyse, Compare, Contrast, Distinguish", "4-8", "analysis and comparison"),
                5: ("Evaluate, Discuss, Examine, Justify, To what extent", "8-15", "synthesis, evaluation, and critical argument"),
            }
            lvl = min(max(difficulty_level, 1), 5)
            terms, marks_range, focus = difficulty_map[lvl]
            difficulty_guidance = f"""
ADAPTIVE DIFFICULTY — LEVEL {lvl}/5:
- Use ONLY these command terms: {terms}
- Mark allocations should be in the range: {marks_range} marks
- Focus on: {focus}
- {'Keep questions simple and direct.' if lvl <= 2 else 'Require nuanced, multi-perspective answers.' if lvl >= 4 else 'Balance clarity with depth.'}
"""

        prompt = f"""You are an IB {display_subject} ({level}) Chief Examiner.

PAST PAPER EXAMPLES (for style reference):
{context_papers}

MARK SCHEME EXCERPTS (for criteria reference):
{context_marks}
{syllabus_context}
{subject_guidance}{difficulty_guidance}
TASK: Generate exactly {count + 2} NEW exam-style questions on the topic "{topic}".

RULES:
1. Each question must use an official IB command term (e.g., Explain, Evaluate, Discuss, Analyse, Compare, Outline, To what extent, Define, Describe, Distinguish, Suggest, Examine, Justify).
2. Assign realistic mark allocations (short answer: 2-4 marks, structured: 6-8 marks, essay: 10-15 marks).
3. Questions must be NOVEL — do not copy from the examples above.
4. Match the difficulty and phrasing style of real IB papers.
5. Style preference: {style}
6. CRITICAL: This is a TEXT-ONLY interface. Students answer by writing text. Do NOT generate questions that require drawing, sketching, labelling images, annotating figures, or any visual/graphical response. Every question must be fully answerable in written prose.
7. Each question must be a complete, self-contained question — at least one full sentence. Never generate single-word or incomplete questions.
8. Questions MUST be based on the IB syllabus content listed above. Do not test content outside the syllabus.

For EACH question, also provide a concise MODEL ANSWER that would earn full marks.

FORMAT your response as exactly {count + 2} questions, each on its own block:
QUESTION: [the question text]
COMMAND_TERM: [the IB command term used]
MARKS: [integer mark allocation]
TOPIC: [specific sub-topic]
MODEL_ANSWER: [a concise model answer that would earn full marks — use bullet points for clarity]
---"""

        response = self.model.generate_content(prompt)
        text = response.text

        questions: list[GeneratedQuestion] = []
        blocks = text.split("---")
        for block in blocks:
            block = block.strip()
            if not block or "QUESTION:" not in block:
                continue
            q_text = _extract_field(block, "QUESTION")
            cmd = _extract_field(block, "COMMAND_TERM")
            marks_str = _extract_field(block, "MARKS")
            q_topic = _extract_field(block, "TOPIC")
            model_answer = _extract_multiline_field(block, "MODEL_ANSWER")

            # Skip garbage questions: too short, single-word, or diagram-only
            if len(q_text.split()) < 5:
                continue
            skip_terms = {"draw", "sketch", "label", "annotate", "construct a graph"}
            if cmd.lower() in skip_terms:
                continue

            try:
                marks = int(marks_str)
            except (ValueError, TypeError):
                marks = 4
            questions.append(
                GeneratedQuestion(
                    question_text=q_text,
                    command_term=cmd,
                    marks=marks,
                    topic=q_topic or topic,
                    source_context=context_papers[:500],
                    model_answer=model_answer,
                )
            )
            if len(questions) >= count:
                break

        return questions

    # ── Live calibration — Grade boundaries ────────────────────────

    def fetch_latest_boundaries(
        self, subject: str, level: str = "HL"
    ) -> GradeBoundary:
        """
        Use Gemini with Google Search grounding to find the latest
        published IB grade boundaries for a given subject.
        """
        prompt = f"""Search for the most recently published IB Diploma Programme grade
boundaries for "{subject.replace('_', ' ').title()}" at {level} level.

Look for the May or November examination session boundaries.

Return the information in this exact format:
SESSION: [e.g. May 2025]
SUBJECT: {subject.replace('_', ' ').title()}
LEVEL: {level}
GRADE_7: [minimum mark for grade 7]
GRADE_6: [minimum mark for grade 6]
GRADE_5: [minimum mark for grade 5]
GRADE_4: [minimum mark for grade 4]
GRADE_3: [minimum mark for grade 3]
GRADE_2: [minimum mark for grade 2]
GRADE_1: [minimum mark for grade 1]
NOTES: [any caveats about the data]

If you cannot find exact boundaries, provide your best estimate based on
historical trends and clearly state it is an estimate."""

        try:
            response = self.model.generate_content(prompt)
            raw = response.text
        except Exception as e:
            return GradeBoundary(
                subject=subject,
                level=level,
                session="unknown",
                boundaries={},
                raw_text=f"Search grounding failed: {e}",
            )

        boundaries: dict[int, int] = {}
        session = "unknown"
        for line in raw.splitlines():
            line = line.strip()
            if line.startswith("SESSION:"):
                session = line.split(":", 1)[1].strip()
            for grade in range(1, 8):
                tag = f"GRADE_{grade}:"
                if line.startswith(tag):
                    try:
                        boundaries[grade] = int(
                            "".join(c for c in line.split(":", 1)[1] if c.isdigit())
                        )
                    except ValueError:
                        pass

        return GradeBoundary(
            subject=subject,
            level=level,
            session=session,
            boundaries=boundaries,
            raw_text=raw,
        )

    # ── Generic Gemini call ────────────────────────────────────────

    def ask(self, prompt: str, system: str = "") -> str:
        """Simple wrapper for ad-hoc Gemini calls."""
        full = f"{system}\n\n{prompt}" if system else prompt
        response = self.model.generate_content(full)
        return response.text


def _extract_field(block: str, field: str) -> str:
    for line in block.splitlines():
        if line.strip().upper().startswith(field.upper() + ":"):
            return line.split(":", 1)[1].strip()
    return ""


def _extract_multiline_field(block: str, field: str) -> str:
    """Extract a field that may span multiple lines (e.g., MODEL_ANSWER)."""
    lines = block.splitlines()
    collecting = False
    result = []
    # Known single-line fields that signal end of multiline content
    stop_fields = {"QUESTION", "COMMAND_TERM", "MARKS", "TOPIC", "MODEL_ANSWER"}
    stop_fields.discard(field.upper())

    for line in lines:
        stripped = line.strip()
        if stripped.upper().startswith(field.upper() + ":"):
            collecting = True
            first_line = stripped.split(":", 1)[1].strip()
            if first_line:
                result.append(first_line)
            continue
        if collecting:
            # Stop if we hit another known field
            if any(stripped.upper().startswith(sf + ":") for sf in stop_fields):
                break
            if stripped:
                result.append(stripped)
    return "\n".join(result)
