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

try:
    import google.generativeai as genai
except ImportError:
    genai = None
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
    keyword_score: float = 0.0
    relevance_score: float = 0.0


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
        self.model = None
        if genai is not None:
            api_key = os.getenv("GOOGLE_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel("gemini-2.0-flash")
        self._vector_store = None

    # ── Vector store access ────────────────────────────────────────

    def _get_store(self):
        """Lazily initialise vector store on first access."""
        if self._vector_store is None:
            from vector_store import get_vector_store
            self._vector_store = get_vector_store()
        return self._vector_store

    @property
    def collection(self):
        """Backwards-compatible access to the underlying collection."""
        return self._get_store()._get_collection()

    def collection_stats(self) -> dict:
        """Return summary stats about ingested documents."""
        try:
            store = self._get_store()
        except Exception:
            return {"count": 0, "subjects": [], "doc_types": []}

        data = store.get()
        metadatas = data.get("metadatas", [])
        subjects = sorted({m.get("subject", "unknown") for m in metadatas})
        doc_types = sorted({m.get("doc_type", "unknown") for m in metadatas})
        sources = sorted({m.get("source", "unknown") for m in metadatas})
        return {
            "count": store.count(),
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

        store = self._get_store()
        results = store.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where_filter,
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

    # ── Hybrid search ─────────────────────────────────────────────

    def hybrid_query(
        self,
        query_text: str,
        n_results: int = 5,
        subject: Optional[str] = None,
        doc_type: Optional[str] = None,
        level: Optional[str] = None,
        alpha: float = 0.7,
    ) -> list[RetrievedChunk]:
        """Hybrid search combining vector similarity and keyword matching.

        Args:
            alpha: Weight for vector score (1-alpha for keyword score).
        """
        # Over-fetch via vector search
        vector_chunks = self.query(
            query_text, n_results=n_results * 2,
            subject=subject, doc_type=doc_type, level=level,
        )

        if not vector_chunks:
            return []

        # Tokenize query for keyword matching
        query_tokens = set(query_text.lower().split())

        for chunk in vector_chunks:
            # Compute keyword score
            chunk_tokens = set(chunk.text.lower().split())
            matching = query_tokens & chunk_tokens
            chunk.keyword_score = (
                len(matching) / len(query_tokens) if query_tokens else 0.0
            )
            # Combine scores
            vector_score = max(0, 1 - chunk.distance)
            chunk.relevance_score = (
                alpha * vector_score + (1 - alpha) * chunk.keyword_score
            )

        # Sort by combined score and return top n
        vector_chunks.sort(key=lambda c: c.relevance_score, reverse=True)
        return vector_chunks[:n_results]

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """LLM-based re-ranking of retrieved chunks.

        Prompts the LLM to rate each chunk's relevance 1-5, then re-sorts.
        Only called when explicitly requested (not default path).
        """
        if not chunks:
            return []

        chunk_descriptions = "\n".join(
            f"[{i}] {c.text[:200]}..." for i, c in enumerate(chunks)
        )
        prompt = (
            f"Query: {query}\n\n"
            f"Rate each chunk's relevance to the query on a scale of 1-5:\n\n"
            f"{chunk_descriptions}\n\n"
            "Respond with ONLY the scores as a comma-separated list of integers, "
            "one per chunk. Example: 5,3,4,1,2"
        )

        try:
            from ai_resilience import resilient_llm_call

            text, _ = resilient_llm_call("gemini", "gemini-2.0-flash", prompt)
            scores = []
            for s in text.strip().split(","):
                try:
                    scores.append(int(s.strip()))
                except ValueError:
                    scores.append(3)  # default to middle score

            # Pad or truncate scores to match chunks
            while len(scores) < len(chunks):
                scores.append(3)

            for i, chunk in enumerate(chunks):
                chunk.relevance_score = float(scores[i]) / 5.0

            chunks.sort(key=lambda c: c.relevance_score, reverse=True)
        except Exception:
            pass  # Return chunks in original order on failure

        return chunks[:top_k]

    # ── Examiner report retrieval ─────────────────────────────────

    def get_examiner_warnings(
        self, subject: str, topic: str
    ) -> list[str]:
        """Query examiner report chunks for warnings about a topic.

        Returns list of warning strings like:
        "60% of students lost marks because they failed to define key terms"
        """
        try:
            chunks = self.query(
                query_text=f"{subject} {topic} common errors candidates lost marks",
                n_results=5,
                subject=subject if subject != "any" else None,
                doc_type="examiner_report",
            )
        except (FileNotFoundError, Exception):
            return []

        warnings: list[str] = []
        for chunk in chunks:
            # Extract sentences that contain examiner warning patterns
            for sentence in chunk.text.split("."):
                sentence = sentence.strip()
                lower = sentence.lower()
                triggers = [
                    "candidates", "students", "marks were lost",
                    "common error", "many failed", "poorly",
                    "frequent mistake", "often lost",
                ]
                if any(t in lower for t in triggers) and len(sentence) > 20:
                    warnings.append(sentence.strip() + ".")
                    if len(warnings) >= 5:
                        break
            if len(warnings) >= 5:
                break

        return warnings

    def get_mark_scheme_criteria(
        self, subject: str, question_type: str, marks: int
    ) -> list[str]:
        """Retrieve specific mark allocation criteria for a question type.

        Returns list of criteria strings like:
        "M1: correct substitution into formula"
        """
        try:
            chunks = self.query(
                query_text=f"{subject} {question_type} {marks} marks mark scheme criteria",
                n_results=4,
                subject=subject if subject != "any" else None,
                doc_type="mark_scheme",
            )
        except (FileNotFoundError, Exception):
            return []

        criteria: list[str] = []
        import re
        for chunk in chunks:
            # Extract mark type lines (M1, A1, R1, etc.)
            for line in chunk.text.splitlines():
                stripped = line.strip()
                if re.search(r"\b[MARCN]\d\b", stripped):
                    criteria.append(stripped)
                elif stripped.startswith("- ") or stripped.startswith("• "):
                    criteria.append(stripped.lstrip("-• "))
                if len(criteria) >= 10:
                    break
            if len(criteria) >= 10:
                break

        return criteria

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

        from ai_resilience import resilient_llm_call

        text, _ = resilient_llm_call("gemini", "gemini-2.0-flash", prompt)

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
            from ai_resilience import resilient_llm_call as _rlc

            raw, _ = _rlc("gemini", "gemini-2.0-flash", prompt)
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
        """Simple wrapper for ad-hoc Gemini calls with resilience."""
        from ai_resilience import resilient_llm_call

        text, _ = resilient_llm_call("gemini", "gemini-2.0-flash", prompt, system=system)
        return text


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
