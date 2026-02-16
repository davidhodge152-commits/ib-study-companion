"""
IB Lifecycle Management — EE, IA, TOK, CAS Tracking

Tracks the full IB diploma lifecycle beyond just exams:
  - Extended Essay (4000-word research paper)
  - Internal Assessments (one per subject)
  - Theory of Knowledge (essay + exhibition)
  - CAS (Creativity, Activity, Service) portfolio

All data persists to session_data/lifecycle.json.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
from datetime import datetime

SESSION_DIR = Path(__file__).parent / "session_data"
SESSION_DIR.mkdir(exist_ok=True)
LIFECYCLE_PATH = SESSION_DIR / "lifecycle.json"


@dataclass
class Milestone:
    id: str
    title: str
    due_date: str = ""       # ISO date, student-set
    completed: bool = False
    completed_date: str = ""
    notes: str = ""


@dataclass
class ExtendedEssay:
    subject: str = ""
    research_question: str = ""
    supervisor: str = ""
    word_count: int = 0
    milestones: list[Milestone] = field(default_factory=lambda: [
        Milestone("ee_topic", "Topic approved"),
        Milestone("ee_outline", "Outline complete"),
        Milestone("ee_draft1", "First draft"),
        Milestone("ee_feedback", "Supervisor feedback received"),
        Milestone("ee_draft2", "Final draft"),
        Milestone("ee_submit", "Submitted"),
    ])


@dataclass
class InternalAssessment:
    subject: str = ""
    title: str = ""
    word_count: int = 0
    milestones: list[Milestone] = field(default_factory=lambda: [
        Milestone("ia_topic", "Topic chosen"),
        Milestone("ia_research", "Research complete"),
        Milestone("ia_draft", "First draft"),
        Milestone("ia_submit", "Submitted"),
    ])


@dataclass
class CASReflection:
    id: str = ""
    strand: str = ""       # "Creativity"|"Activity"|"Service"
    title: str = ""
    description: str = ""
    date: str = ""
    learning_outcome: str = ""  # Which of the 7 CAS learning outcomes
    hours: float = 0


@dataclass
class TOKProgress:
    essay_title: str = ""
    prescribed_title_number: int = 0
    exhibition_theme: str = ""
    milestones: list[Milestone] = field(default_factory=lambda: [
        Milestone("tok_title", "Prescribed title selected"),
        Milestone("tok_outline", "Essay outline"),
        Milestone("tok_draft", "First draft"),
        Milestone("tok_submit", "Essay submitted"),
        Milestone("tok_exhibition", "Exhibition complete"),
    ])


# The 7 CAS learning outcomes
CAS_LEARNING_OUTCOMES = [
    "Identify own strengths and develop areas for growth",
    "Demonstrate that challenges have been undertaken, developing new skills",
    "Demonstrate how to initiate and plan a CAS experience",
    "Show commitment to and perseverance in CAS experiences",
    "Demonstrate the skills and recognise the benefits of working collaboratively",
    "Demonstrate engagement with issues of global significance",
    "Recognise and consider the ethics of choices and actions",
]


@dataclass
class IBLifecycle:
    extended_essay: ExtendedEssay = field(default_factory=ExtendedEssay)
    internal_assessments: list[InternalAssessment] = field(default_factory=list)
    tok: TOKProgress = field(default_factory=TOKProgress)
    cas_reflections: list[CASReflection] = field(default_factory=list)
    cas_hours: dict[str, float] = field(default_factory=lambda: {
        "Creativity": 0, "Activity": 0, "Service": 0,
    })

    def total_milestones(self) -> int:
        """Count all milestones across EE, IAs, and TOK."""
        count = len(self.extended_essay.milestones)
        count += len(self.tok.milestones)
        for ia in self.internal_assessments:
            count += len(ia.milestones)
        return count

    def completed_milestones(self) -> int:
        """Count completed milestones across EE, IAs, and TOK."""
        count = sum(1 for m in self.extended_essay.milestones if m.completed)
        count += sum(1 for m in self.tok.milestones if m.completed)
        for ia in self.internal_assessments:
            count += sum(1 for m in ia.milestones if m.completed)
        return count

    def next_milestone(self, section: str = "all") -> Optional[Milestone]:
        """Return the next incomplete milestone for a section or overall."""
        milestones: list[Milestone] = []
        if section in ("ee", "all"):
            milestones.extend(self.extended_essay.milestones)
        if section in ("tok", "all"):
            milestones.extend(self.tok.milestones)
        if section in ("ia", "all"):
            for ia in self.internal_assessments:
                milestones.extend(ia.milestones)

        for m in milestones:
            if not m.completed:
                return m
        return None

    def toggle_milestone(self, milestone_id: str) -> bool:
        """Toggle a milestone's completed status. Returns new state."""
        for m in self._all_milestones():
            if m.id == milestone_id:
                m.completed = not m.completed
                m.completed_date = datetime.now().isoformat() if m.completed else ""
                self.save()
                return m.completed
        return False

    def update_cas_hours(self) -> None:
        """Recalculate CAS hours from reflections."""
        self.cas_hours = {"Creativity": 0, "Activity": 0, "Service": 0}
        for r in self.cas_reflections:
            if r.strand in self.cas_hours:
                self.cas_hours[r.strand] += r.hours

    def add_cas_reflection(self, reflection: CASReflection) -> None:
        """Add a CAS reflection and update hours."""
        if not reflection.id:
            reflection.id = f"cas_{len(self.cas_reflections) + 1}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.cas_reflections.append(reflection)
        self.update_cas_hours()
        self.save()

    def get_ia_for_subject(self, subject: str) -> Optional[InternalAssessment]:
        """Find the IA for a specific subject."""
        for ia in self.internal_assessments:
            if ia.subject == subject:
                return ia
        return None

    def _all_milestones(self) -> list[Milestone]:
        """Get all milestones from all sections."""
        milestones = list(self.extended_essay.milestones)
        milestones.extend(self.tok.milestones)
        for ia in self.internal_assessments:
            milestones.extend(ia.milestones)
        return milestones

    def save(self) -> None:
        """Persist lifecycle data to JSON."""
        data = {
            "extended_essay": _ee_to_dict(self.extended_essay),
            "internal_assessments": [_ia_to_dict(ia) for ia in self.internal_assessments],
            "tok": _tok_to_dict(self.tok),
            "cas_reflections": [asdict(r) for r in self.cas_reflections],
            "cas_hours": self.cas_hours,
        }
        LIFECYCLE_PATH.write_text(json.dumps(data, indent=2))

    @staticmethod
    def load() -> IBLifecycle:
        """Load lifecycle from JSON, or return a fresh instance."""
        if not LIFECYCLE_PATH.exists():
            return IBLifecycle()
        try:
            data = json.loads(LIFECYCLE_PATH.read_text())
            lifecycle = IBLifecycle()

            # Extended Essay
            ee_data = data.get("extended_essay", {})
            lifecycle.extended_essay = ExtendedEssay(
                subject=ee_data.get("subject", ""),
                research_question=ee_data.get("research_question", ""),
                supervisor=ee_data.get("supervisor", ""),
                word_count=ee_data.get("word_count", 0),
                milestones=_load_milestones(ee_data.get("milestones", []),
                                            ExtendedEssay().milestones),
            )

            # Internal Assessments
            for ia_data in data.get("internal_assessments", []):
                lifecycle.internal_assessments.append(InternalAssessment(
                    subject=ia_data.get("subject", ""),
                    title=ia_data.get("title", ""),
                    word_count=ia_data.get("word_count", 0),
                    milestones=_load_milestones(ia_data.get("milestones", []),
                                                InternalAssessment().milestones),
                ))

            # TOK
            tok_data = data.get("tok", {})
            lifecycle.tok = TOKProgress(
                essay_title=tok_data.get("essay_title", ""),
                prescribed_title_number=tok_data.get("prescribed_title_number", 0),
                exhibition_theme=tok_data.get("exhibition_theme", ""),
                milestones=_load_milestones(tok_data.get("milestones", []),
                                            TOKProgress().milestones),
            )

            # CAS
            for cas_data in data.get("cas_reflections", []):
                lifecycle.cas_reflections.append(CASReflection(
                    id=cas_data.get("id", ""),
                    strand=cas_data.get("strand", ""),
                    title=cas_data.get("title", ""),
                    description=cas_data.get("description", ""),
                    date=cas_data.get("date", ""),
                    learning_outcome=cas_data.get("learning_outcome", ""),
                    hours=cas_data.get("hours", 0),
                ))
            lifecycle.cas_hours = data.get("cas_hours", {
                "Creativity": 0, "Activity": 0, "Service": 0,
            })

            return lifecycle
        except (json.JSONDecodeError, KeyError, TypeError):
            return IBLifecycle()

    def init_from_profile(self, subjects: list[str]) -> None:
        """Auto-populate IAs from student's subject list (skip Core subjects)."""
        core_subjects = {"Theory of Knowledge", "Extended Essay"}
        existing = {ia.subject for ia in self.internal_assessments}
        for subject in subjects:
            if subject not in core_subjects and subject not in existing:
                self.internal_assessments.append(InternalAssessment(
                    subject=subject,
                    milestones=[
                        Milestone(f"ia_{_subject_key(subject)}_topic", "Topic chosen"),
                        Milestone(f"ia_{_subject_key(subject)}_research", "Research complete"),
                        Milestone(f"ia_{_subject_key(subject)}_draft", "First draft"),
                        Milestone(f"ia_{_subject_key(subject)}_submit", "Submitted"),
                    ],
                ))
        self.save()

    def summary(self) -> dict:
        """Return a summary for dashboard display."""
        total = self.total_milestones()
        completed = self.completed_milestones()
        return {
            "total_milestones": total,
            "completed_milestones": completed,
            "progress_pct": round(completed / total * 100) if total > 0 else 0,
            "ee_subject": self.extended_essay.subject,
            "ee_rq": self.extended_essay.research_question,
            "ee_progress": _section_progress(self.extended_essay.milestones),
            "tok_title": self.tok.essay_title,
            "tok_progress": _section_progress(self.tok.milestones),
            "ia_count": len(self.internal_assessments),
            "ia_summaries": [
                {
                    "subject": ia.subject,
                    "title": ia.title,
                    "progress": _section_progress(ia.milestones),
                }
                for ia in self.internal_assessments
            ],
            "cas_hours": self.cas_hours,
            "cas_reflections_count": len(self.cas_reflections),
        }


def _subject_key(name: str) -> str:
    return name.lower().split(":")[0].strip().replace(" ", "_").replace("&", "")


def _section_progress(milestones: list[Milestone]) -> dict:
    total = len(milestones)
    completed = sum(1 for m in milestones if m.completed)
    next_m = next((m for m in milestones if not m.completed), None)
    return {
        "total": total,
        "completed": completed,
        "pct": round(completed / total * 100) if total > 0 else 0,
        "next": next_m.title if next_m else "All complete",
    }


def _milestone_to_dict(m: Milestone) -> dict:
    return {
        "id": m.id, "title": m.title, "due_date": m.due_date,
        "completed": m.completed, "completed_date": m.completed_date,
        "notes": m.notes,
    }


def _load_milestones(data: list[dict], defaults: list[Milestone]) -> list[Milestone]:
    """Load milestones from saved data, falling back to defaults for missing ones."""
    if not data:
        return defaults
    loaded = []
    for d in data:
        loaded.append(Milestone(
            id=d.get("id", ""),
            title=d.get("title", ""),
            due_date=d.get("due_date", ""),
            completed=d.get("completed", False),
            completed_date=d.get("completed_date", ""),
            notes=d.get("notes", ""),
        ))
    return loaded


def _ee_to_dict(ee: ExtendedEssay) -> dict:
    return {
        "subject": ee.subject, "research_question": ee.research_question,
        "supervisor": ee.supervisor, "word_count": ee.word_count,
        "milestones": [_milestone_to_dict(m) for m in ee.milestones],
    }


def _ia_to_dict(ia: InternalAssessment) -> dict:
    return {
        "subject": ia.subject, "title": ia.title, "word_count": ia.word_count,
        "milestones": [_milestone_to_dict(m) for m in ia.milestones],
    }


def _tok_to_dict(tok: TOKProgress) -> dict:
    return {
        "essay_title": tok.essay_title,
        "prescribed_title_number": tok.prescribed_title_number,
        "exhibition_theme": tok.exhibition_theme,
        "milestones": [_milestone_to_dict(m) for m in tok.milestones],
    }
