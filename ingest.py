"""
The Archivist — Ingestion & RAG Engine

Parses PDFs from the ./data folder, chunks them intelligently by
question type and section boundaries, and stores embeddings in ChromaDB.

Usage:
    python ingest.py              # Ingest all PDFs in ./data
    python ingest.py --reset      # Wipe the vector store and re-ingest
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path

try:
    import chromadb
except ImportError:
    chromadb = None
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

DATA_DIR = Path(__file__).parent / "data"
CHROMA_DIR = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "ib_documents"

# ── Chunking heuristics ────────────────────────────────────────────

# Patterns that signal a new logical section in IB papers / mark schemes
SECTION_BREAK = re.compile(
    r"(?i)"
    r"(?:^|\n)"
    r"(?:"
    r"(?:question|q)\s*\d+"           # "Question 3" / "Q3"
    r"|section\s+[a-z]"              # "Section A"
    r"|paper\s+\d"                   # "Paper 2"
    r"|part\s+\([a-z]\)"            # "Part (a)"
    r"|topic\s+\d+"                  # "Topic 4"
    r"|criterion\s+[a-z]"           # "Criterion A"  (EE / IA rubrics)
    r"|markband"                     # Markband tables
    r"|assessment\s+criteria"        # Generic rubric header
    r")"
)


def classify_document(filename: str, text_sample: str) -> str:
    """Return a document‑type tag used as ChromaDB metadata."""
    name = filename.lower()
    sample = text_sample[:2000].lower()

    if "mark" in name and "scheme" in name or "markscheme" in name:
        return "mark_scheme"
    if "mark scheme" in sample or "markscheme" in sample or "markband" in sample:
        return "mark_scheme"
    if "paper" in name or "exam" in name or "past" in name:
        return "past_paper"
    if "guide" in name or "syllabus" in name:
        return "subject_guide"
    if any(kw in sample for kw in ("syllabus content", "assessment outline", "aims")):
        return "subject_guide"
    return "notes"


def detect_subject(filename: str, text_sample: str) -> str:
    """Best-effort extraction of the IB subject from filename / content."""
    subjects = [
        "biology", "chemistry", "physics", "mathematics", "math",
        "english", "history", "geography", "economics", "psychology",
        "philosophy", "computer science", "visual arts", "music",
        "french", "spanish", "german", "mandarin", "tok",
        "theory of knowledge", "extended essay", "business management",
        "environmental systems", "ess", "global politics",
    ]
    combined = (filename + " " + text_sample[:1500]).lower()
    for subj in subjects:
        if subj in combined:
            return subj.replace(" ", "_")
    return "unknown"


def detect_level(filename: str, text_sample: str) -> str:
    """Detect HL / SL from filename or text."""
    combined = (filename + " " + text_sample[:1000]).lower()
    if "higher level" in combined or "(hl)" in combined or "_hl" in combined or " hl " in combined:
        return "HL"
    if "standard level" in combined or "(sl)" in combined or "_sl" in combined or " sl " in combined:
        return "SL"
    return "unknown"


def parse_examiner_report(text: str) -> list[dict]:
    """Extract per-question examiner commentary from an examiner report.

    Returns list of dicts with keys:
        question_num, topic, common_errors, examiner_advice, marks_lost_pct
    """
    entries: list[dict] = []
    current: dict | None = None

    for line in text.splitlines():
        stripped = line.strip()

        # Detect question headers
        q_match = re.match(r"(?i)(?:question|q)\s*(\d+[a-z]?)", stripped)
        if q_match:
            if current:
                entries.append(current)
            current = {
                "question_num": q_match.group(1),
                "topic": "",
                "common_errors": [],
                "examiner_advice": "",
                "marks_lost_pct": 0,
            }
            continue

        if current is None:
            continue

        low = stripped.lower()

        # Topic detection
        if low.startswith("topic:") or low.startswith("syllabus:"):
            current["topic"] = stripped.split(":", 1)[1].strip()

        # Common errors
        error_triggers = [
            "common error", "many candidates", "frequent mistake",
            "students often", "most candidates", "candidates failed",
            "poorly answered", "marks were lost", "candidates lost marks",
        ]
        if any(t in low for t in error_triggers):
            current["common_errors"].append(stripped)

        # Advice
        advice_triggers = [
            "candidates should", "it is recommended", "students are advised",
            "to improve", "better answers", "stronger responses",
        ]
        if any(t in low for t in advice_triggers):
            current["examiner_advice"] += stripped + " "

        # Percentage of marks lost
        pct_match = re.search(r"(\d{1,3})%", stripped)
        if pct_match and any(t in low for t in ["lost", "failed", "incorrect"]):
            try:
                current["marks_lost_pct"] = int(pct_match.group(1))
            except ValueError:
                pass

    if current:
        entries.append(current)

    # Clean up advice strings
    for e in entries:
        e["examiner_advice"] = e["examiner_advice"].strip()

    return entries


def parse_mark_scheme(text: str) -> list[dict]:
    """Extract structured mark allocations from a mark scheme.

    Returns list of dicts with keys:
        question_num, marks, mark_types, criteria
    """
    entries: list[dict] = []
    current: dict | None = None

    for line in text.splitlines():
        stripped = line.strip()

        # Detect question headers
        q_match = re.match(r"(?i)(?:question|q)\s*(\d+[a-z]?)", stripped)
        if q_match:
            if current:
                entries.append(current)
            current = {
                "question_num": q_match.group(1),
                "marks": 0,
                "mark_types": [],
                "criteria": [],
            }
            # Check for mark allocation on the same line as question header
            mark_match = re.search(r"[\[\(](\d+)\s*(?:marks?)?[\]\)]", stripped)
            if mark_match:
                try:
                    current["marks"] = int(mark_match.group(1))
                except ValueError:
                    pass
            continue

        if current is None:
            continue

        # Mark types: M1, A1, R1, C1, etc.
        mark_codes = re.findall(r"\b([MARCN]\d)\b", stripped)
        if mark_codes:
            current["mark_types"].extend(mark_codes)
            # Only update marks from codes if no explicit allocation set
            if current["marks"] == 0:
                current["marks"] = len(current["mark_types"])
            current["criteria"].append(stripped)

        # Explicit mark allocation "[3 marks]" or "(3)" on subsequent lines
        mark_match = re.search(r"[\[\(](\d+)\s*(?:marks?)?[\]\)]", stripped)
        if mark_match and not mark_codes:
            try:
                current["marks"] = int(mark_match.group(1))
            except ValueError:
                pass

        # Criteria lines (bullet points or numbered)
        if re.match(r"^[-•]\s+", stripped) or re.match(r"^\d+\.", stripped):
            current["criteria"].append(stripped.lstrip("-•0123456789. "))

    if current:
        entries.append(current)

    return entries


def detect_year(filename: str, text_sample: str) -> int:
    """Extract exam year from filename or text."""
    combined = filename + " " + text_sample[:1000]
    year_match = re.search(r"(20[12]\d)", combined)
    if year_match:
        try:
            return int(year_match.group(1))
        except ValueError:
            pass
    return 0


def detect_session(filename: str, text_sample: str) -> str:
    """Detect May/November session."""
    combined = (filename + " " + text_sample[:1000]).lower()
    if "november" in combined or "nov" in combined:
        return "Nov"
    if "may" in combined:
        return "May"
    return ""


def detect_paper_number(filename: str, text_sample: str) -> int:
    """Detect paper number (1, 2, 3)."""
    combined = (filename + " " + text_sample[:500]).lower()
    match = re.search(r"paper\s*(\d)", combined)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    return 0


def validate_chunk(text: str) -> tuple[bool, str]:
    """Validate a text chunk for quality. Returns (is_valid, reason)."""
    if len(text) < 50:
        return False, f"too short ({len(text)} chars, min 50)"
    if len(text) > 4000:
        return False, f"too long ({len(text)} chars, max 4000)"
    alpha_chars = sum(1 for c in text if c.isalpha())
    total_chars = len(text)
    alpha_ratio = alpha_chars / total_chars if total_chars > 0 else 0
    if alpha_ratio < 0.3:
        return False, f"low alpha ratio ({alpha_ratio:.2f}, min 0.3)"
    return True, ""


def chunk_text(text: str, max_tokens: int = 800) -> list[str]:
    """
    Split text into chunks, preferring section boundaries.

    Approximate token count via whitespace splitting (1 token ≈ 1 word).
    """
    parts = SECTION_BREAK.split(text)
    chunks: list[str] = []
    buffer = ""

    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len((buffer + " " + part).split()) <= max_tokens:
            buffer = (buffer + "\n\n" + part).strip()
        else:
            if buffer:
                chunks.append(buffer)
            # If a single part exceeds max_tokens, split by paragraphs
            if len(part.split()) > max_tokens:
                paragraphs = part.split("\n\n")
                sub = ""
                for para in paragraphs:
                    if len((sub + " " + para).split()) <= max_tokens:
                        sub = (sub + "\n\n" + para).strip()
                    else:
                        if sub:
                            chunks.append(sub)
                        sub = para
                buffer = sub
            else:
                buffer = part

    if buffer:
        chunks.append(buffer)

    return chunks


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def extract_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n\n".join(pages)


def extract_text_from_image(image_path: Path) -> str:
    """Use Gemini Vision to OCR text from an image file."""
    try:
        import google.generativeai as genai
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return ""
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")

        import PIL.Image
        img = PIL.Image.open(str(image_path))
        response = model.generate_content([
            "Extract ALL text from this image. Preserve the original formatting, "
            "headings, and structure as closely as possible. If this is an IB exam paper "
            "or mark scheme, maintain question numbers and mark allocations.",
            img,
        ])
        return response.text
    except ImportError:
        return ""
    except Exception:
        return ""


def ingest_uploaded_file(
    save_path: str,
    filename: str,
    doc_type: str,
    is_image: bool = False,
) -> dict:
    """Standalone ingestion function that doesn't need Flask request context.

    Designed to be called via tasks.enqueue() for background processing.
    Returns a dict with ingestion results.
    """
    save_path = Path(save_path)

    text = extract_text_from_image(save_path) if is_image else extract_text(save_path)
    if not text.strip():
        return {"error": "No extractable text", "success": False}

    detected_type = doc_type if doc_type != "auto" else classify_document(filename, text)
    subject = detect_subject(filename, text)
    level = detect_level(filename, text)
    chunks = chunk_text(text)
    fhash = file_hash(save_path)
    prefix = f"{save_path.stem}_{fhash}"

    from vector_store import get_vector_store
    store = get_vector_store()

    ids = [f"{prefix}_c{i:04d}" for i in range(len(chunks))]
    metadatas = [
        {
            "source": filename,
            "doc_type": detected_type,
            "subject": subject,
            "level": level,
            "chunk_index": i,
            "total_chunks": len(chunks),
        }
        for i in range(len(chunks))
    ]

    store.add(ids=ids, documents=chunks, metadatas=metadatas)

    return {
        "success": True,
        "filename": filename,
        "doc_type": detected_type,
        "subject": subject,
        "level": level,
        "chunks": len(chunks),
        "text": text,
    }


def ingest(reset: bool = False) -> None:
    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True)
        print(f"[Archivist] Created data folder at {DATA_DIR}")
        print("[Archivist] Drop your IB PDFs there and re-run this script.")
        return

    pdfs = sorted(DATA_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"[Archivist] No PDFs found in {DATA_DIR}")
        print("[Archivist] Add your Past Papers, Mark Schemes, or Notes as PDF files.")
        return

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
            print("[Archivist] Existing collection wiped.")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    existing_ids = set(collection.get()["ids"]) if collection.count() > 0 else set()

    total_chunks = 0
    for pdf in pdfs:
        fhash = file_hash(pdf)
        prefix = f"{pdf.stem}_{fhash}"

        # Skip if already ingested (any chunk with this prefix exists)
        if any(eid.startswith(prefix) for eid in existing_ids):
            print(f"  [skip] {pdf.name} (already ingested)")
            continue

        print(f"  [read] {pdf.name} ... ", end="", flush=True)
        try:
            text = extract_text(pdf)
        except Exception as e:
            print(f"ERROR: {e}")
            continue

        if not text.strip():
            print("WARNING: no extractable text (scanned PDF?)")
            continue

        doc_type = classify_document(pdf.name, text)
        subject = detect_subject(pdf.name, text)
        level = detect_level(pdf.name, text)
        year = detect_year(pdf.name, text)
        session = detect_session(pdf.name, text)
        paper_number = detect_paper_number(pdf.name, text)
        raw_chunks = chunk_text(text)
        # Filter out invalid chunks
        chunks = []
        rejected = 0
        for c in raw_chunks:
            valid, reason = validate_chunk(c)
            if valid:
                chunks.append(c)
            else:
                rejected += 1
        if rejected:
            print(f"  ({rejected} chunks rejected) ", end="", flush=True)

        ids = [f"{prefix}_c{i:04d}" for i in range(len(chunks))]
        metadatas = [
            {
                "source": pdf.name,
                "doc_type": doc_type,
                "subject": subject,
                "level": level,
                "year": year,
                "session": session,
                "paper_number": paper_number,
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
            for i in range(len(chunks))
        ]

        collection.add(documents=chunks, ids=ids, metadatas=metadatas)
        total_chunks += len(chunks)
        print(f"{len(chunks)} chunks  [{doc_type} | {subject} | {level}]")

    print(f"\n[Archivist] Done. {total_chunks} new chunks added.")
    print(f"[Archivist] Collection now holds {collection.count()} total chunks.")


if __name__ == "__main__":
    reset_flag = "--reset" in sys.argv
    print("=" * 60)
    print("  IB Study Companion — The Archivist (Ingestion Engine)")
    print("=" * 60)
    ingest(reset=reset_flag)
