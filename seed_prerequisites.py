"""Seed prerequisite edges for the syllabus knowledge graph.

Run: python seed_prerequisites.py

Populates the topic_prerequisites table with pedagogically-sound
prerequisite relationships for all IB subjects.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


# Format: (subject, topic_id, requires_topic_id, strength)
# strength: 1.0 = hard prereq, 0.5 = soft/recommended
PREREQUISITES: list[tuple[str, str, str, float]] = [
    # ── Biology ──────────────────────────────────────────────────
    # Molecular Biology requires Cell Biology
    ("Biology", "bio_2", "bio_1", 1.0),
    # Genetics requires Molecular Biology (DNA structure)
    ("Biology", "bio_3", "bio_2", 1.0),
    # Ecology requires Cell Biology (basic cell functions)
    ("Biology", "bio_4", "bio_1", 0.5),
    # Evolution requires Genetics (natural selection, gene pools)
    ("Biology", "bio_5", "bio_3", 1.0),
    # Human Physiology requires Cell Biology + Molecular Biology
    ("Biology", "bio_6", "bio_1", 1.0),
    ("Biology", "bio_6", "bio_2", 0.5),
    # HL: Nucleic Acids requires Molecular Biology
    ("Biology", "bio_7", "bio_2", 1.0),
    # HL: Metabolism requires Molecular Biology
    ("Biology", "bio_8", "bio_2", 1.0),
    # HL: Plant Biology requires Ecology + Cell Biology
    ("Biology", "bio_9", "bio_1", 0.5),
    ("Biology", "bio_9", "bio_4", 0.5),
    # HL: Genetics and Evolution requires Genetics + Evolution
    ("Biology", "bio_10", "bio_3", 1.0),
    ("Biology", "bio_10", "bio_5", 1.0),
    # HL: Animal Physiology requires Human Physiology
    ("Biology", "bio_11", "bio_6", 1.0),

    # ── Chemistry ────────────────────────────────────────────────
    # Atomic Structure requires Stoichiometry (mole concept)
    ("Chemistry", "chem_2", "chem_1", 0.5),
    # Periodicity requires Atomic Structure
    ("Chemistry", "chem_3", "chem_2", 1.0),
    # Bonding requires Atomic Structure + Periodicity
    ("Chemistry", "chem_4", "chem_2", 1.0),
    ("Chemistry", "chem_4", "chem_3", 0.5),
    # Energetics requires Stoichiometry + Bonding
    ("Chemistry", "chem_5", "chem_1", 1.0),
    ("Chemistry", "chem_5", "chem_4", 0.5),
    # Kinetics requires Energetics
    ("Chemistry", "chem_6", "chem_5", 0.5),
    # Equilibrium requires Kinetics
    ("Chemistry", "chem_7", "chem_6", 1.0),
    # Acids/Bases requires Equilibrium + Bonding
    ("Chemistry", "chem_8", "chem_7", 1.0),
    ("Chemistry", "chem_8", "chem_4", 0.5),
    # Redox requires Atomic Structure + Bonding
    ("Chemistry", "chem_9", "chem_2", 1.0),
    ("Chemistry", "chem_9", "chem_4", 0.5),
    # Organic requires Bonding + Stoichiometry
    ("Chemistry", "chem_10", "chem_4", 1.0),
    ("Chemistry", "chem_10", "chem_1", 0.5),
    # Measurement requires Stoichiometry
    ("Chemistry", "chem_11", "chem_1", 0.5),
    # HL extensions require their SL counterparts
    ("Chemistry", "chem_12", "chem_2", 1.0),
    ("Chemistry", "chem_13", "chem_3", 1.0),
    ("Chemistry", "chem_14", "chem_4", 1.0),
    ("Chemistry", "chem_15", "chem_5", 1.0),
    ("Chemistry", "chem_16", "chem_6", 1.0),
    ("Chemistry", "chem_17", "chem_7", 1.0),
    ("Chemistry", "chem_18", "chem_8", 1.0),
    ("Chemistry", "chem_19", "chem_9", 1.0),
    ("Chemistry", "chem_20", "chem_10", 1.0),

    # ── Physics ──────────────────────────────────────────────────
    # Mechanics requires Measurements
    ("Physics", "phys_2", "phys_1", 1.0),
    # Thermal Physics requires Mechanics (energy concepts)
    ("Physics", "phys_3", "phys_2", 0.5),
    # Waves requires Mechanics (oscillations)
    ("Physics", "phys_4", "phys_2", 0.5),
    # Electricity requires Mechanics (force, energy)
    ("Physics", "phys_5", "phys_2", 1.0),
    # Circular Motion requires Mechanics
    ("Physics", "phys_6", "phys_2", 1.0),
    # Atomic/Nuclear requires Electricity + Waves
    ("Physics", "phys_7", "phys_5", 0.5),
    ("Physics", "phys_7", "phys_4", 0.5),
    # Energy Production requires Thermal Physics + Electricity
    ("Physics", "phys_8", "phys_3", 0.5),
    ("Physics", "phys_8", "phys_5", 0.5),
    # HL: Wave Phenomena requires Waves
    ("Physics", "phys_9", "phys_4", 1.0),
    # HL: Fields requires Circular Motion + Electricity
    ("Physics", "phys_10", "phys_6", 1.0),
    ("Physics", "phys_10", "phys_5", 1.0),
    # HL: EM Induction requires Electricity
    ("Physics", "phys_11", "phys_5", 1.0),
    # HL: Quantum requires Atomic + Wave Phenomena
    ("Physics", "phys_12", "phys_7", 1.0),
    ("Physics", "phys_12", "phys_9", 0.5),

    # ── Economics ─────────────────────────────────────────────────
    ("Economics", "econ_2", "econ_1", 1.0),
    ("Economics", "econ_3", "econ_1", 1.0),
    ("Economics", "econ_3", "econ_2", 0.5),
    ("Economics", "econ_4", "econ_2", 0.5),
    ("Economics", "econ_4", "econ_3", 0.5),

    # ── Mathematics: AA ──────────────────────────────────────────
    # (Topics from subject_config if populated — add when available)
]


def seed(app=None) -> int:
    """Insert prerequisite edges into database. Returns count inserted."""
    if app is None:
        from app import create_app
        app = create_app()

    count = 0
    with app.app_context():
        from database import get_db, init_db, run_migrations
        init_db()
        run_migrations()
        db = get_db()

        for subject, topic_id, requires_topic_id, strength in PREREQUISITES:
            try:
                db.execute(
                    "INSERT OR IGNORE INTO topic_prerequisites "
                    "(subject, topic_id, requires_topic_id, strength) "
                    "VALUES (?, ?, ?, ?)",
                    (subject, topic_id, requires_topic_id, strength),
                )
                count += 1
            except Exception:
                pass

        db.commit()
    return count


if __name__ == "__main__":
    print("=" * 50)
    print("  Seeding Prerequisite Knowledge Graph")
    print("=" * 50)
    n = seed()
    print(f"  {n} prerequisite edges inserted/updated.")
    print("  Done.")
