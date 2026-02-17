"""
Seed Demo Data — Standalone script and pytest fixture.

Creates 5 demo students with varying profiles, 50+ grades, activity log entries,
gamification data, flashcards, and study plans. Creates 1 teacher with a class
containing all demo students.

Usage:
    python seed_demo_data.py           # Seed into the running database
    python seed_demo_data.py --reset   # Clear demo data first
"""

from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash


DEMO_STUDENTS = [
    {"name": "Alice Chen", "email": "alice@demo.ib", "target": 40,
     "subjects": [("Biology", "HL", 6), ("Chemistry", "SL", 5), ("Mathematics: AA", "HL", 7)]},
    {"name": "Bob Tanaka", "email": "bob@demo.ib", "target": 35,
     "subjects": [("Physics", "HL", 6), ("Mathematics: AA", "HL", 6), ("Economics", "SL", 5)]},
    {"name": "Clara Schmidt", "email": "clara@demo.ib", "target": 38,
     "subjects": [("English", "HL", 6), ("History", "HL", 6), ("Psychology", "SL", 5)]},
    {"name": "David Kim", "email": "david@demo.ib", "target": 42,
     "subjects": [("Biology", "HL", 7), ("Chemistry", "HL", 6), ("Mathematics: AA", "HL", 7)]},
    {"name": "Eva Rossi", "email": "eva@demo.ib", "target": 36,
     "subjects": [("Economics", "HL", 6), ("Geography", "SL", 5), ("English", "SL", 5)]},
]

DEMO_TEACHER = {"name": "Dr. Sarah Patel", "email": "teacher@demo.ib"}

COMMAND_TERMS = ["Explain", "Evaluate", "Discuss", "Describe", "Analyse", "Compare", "Define", "Outline"]
TOPICS = ["Topic 1", "Topic 2", "Topic 3", "Topic 4", "Topic 5"]


def seed(db, start_uid: int = 200) -> dict:
    """Seed demo data into the database. Returns summary dict."""
    now = datetime.now()
    password = generate_password_hash("demo123")

    student_ids = []
    grade_count = 0

    # Create students
    for i, student in enumerate(DEMO_STUDENTS):
        uid = start_uid + i
        student_ids.append(uid)

        db.execute(
            "INSERT OR IGNORE INTO users (id, name, email, password_hash, exam_session, "
            "target_total_points, created_at) VALUES (?, ?, ?, ?, 'May 2026', ?, ?)",
            (uid, student["name"], student["email"], password, student["target"], now.isoformat()),
        )
        db.execute("INSERT OR IGNORE INTO gamification (user_id) VALUES (?)", (uid,))

        # Subjects
        for subj, level, target in student["subjects"]:
            db.execute(
                "INSERT OR IGNORE INTO user_subjects (user_id, name, level, target_grade) "
                "VALUES (?, ?, ?, ?)",
                (uid, subj, level, target),
            )

            # 10-15 grades per subject over last 30 days
            num_grades = random.randint(10, 15)
            base_grade = random.randint(3, 5)
            for j in range(num_grades):
                days_ago = 30 - int(j * 30 / num_grades)
                ts = (now - timedelta(days=days_ago, hours=random.randint(8, 20))).isoformat()
                # Grades trend upward
                grade = min(7, base_grade + (j * 3) // num_grades + random.randint(-1, 1))
                grade = max(1, grade)
                pct = min(100, max(10, grade * 14 + random.randint(-5, 5)))
                marks_total = random.choice([4, 6, 8, 10])
                marks_earned = min(marks_total, max(0, round(marks_total * pct / 100)))

                db.execute(
                    "INSERT INTO grades (user_id, subject, subject_display, level, "
                    "command_term, grade, percentage, mark_earned, mark_total, "
                    "strengths, improvements, examiner_tip, topic, timestamp) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (uid, subj.lower().replace(" ", "_").replace(":", ""), subj, level,
                     random.choice(COMMAND_TERMS), grade, pct, marks_earned, marks_total,
                     json.dumps(["Good use of terminology"]),
                     json.dumps(["Needs more examples"]),
                     "Define key terms first", random.choice(TOPICS), ts),
                )
                grade_count += 1

        # Activity log — 15-25 days of activity
        active_days = random.randint(15, 25)
        for d in range(active_days):
            days_ago = random.randint(0, 29)
            dt = now - timedelta(days=days_ago)
            db.execute(
                "INSERT OR IGNORE INTO activity_log (user_id, date, subject, "
                "questions_attempted, duration_minutes, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (uid, dt.strftime("%Y-%m-%d"),
                 random.choice(student["subjects"])[0],
                 random.randint(3, 15),
                 random.randint(15, 90),
                 dt.replace(hour=random.randint(8, 21)).isoformat()),
            )

        # Gamification: streaks and XP
        db.execute(
            "UPDATE gamification SET total_xp = ?, current_streak = ?, longest_streak = ?, "
            "total_questions_answered = ? WHERE user_id = ?",
            (random.randint(500, 3000), random.randint(0, 15),
             random.randint(5, 30), random.randint(20, 200), uid),
        )

        # Flashcards — 5-10 per student
        for k in range(random.randint(5, 10)):
            card_id = f"demo_{uid}_{k}"
            db.execute(
                "INSERT OR IGNORE INTO flashcards (id, user_id, subject, front, back, "
                "next_review, interval_days, ease_factor, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (card_id, uid, random.choice(student["subjects"])[0],
                 f"What is concept {k + 1}?", f"Concept {k + 1} is defined as...",
                 (now + timedelta(days=random.randint(0, 7))).isoformat(),
                 random.choice([1, 2, 4, 7]), 2.5, now.isoformat()),
            )

    # Create teacher
    teacher_uid = start_uid + len(DEMO_STUDENTS)
    db.execute(
        "INSERT OR IGNORE INTO users (id, name, email, password_hash, role, created_at) "
        "VALUES (?, ?, ?, ?, 'teacher', ?)",
        (teacher_uid, DEMO_TEACHER["name"], DEMO_TEACHER["email"], password, now.isoformat()),
    )
    db.execute("INSERT OR IGNORE INTO gamification (user_id) VALUES (?)", (teacher_uid,))

    # Create school and class
    db.execute(
        "INSERT OR IGNORE INTO schools (id, name, code, created_at) "
        "VALUES (100, 'Demo International School', 'DEMO100', ?)",
        (now.isoformat(),),
    )
    db.execute(
        "INSERT OR IGNORE INTO classes (id, school_id, teacher_id, name, subject, level, "
        "join_code, created_at) VALUES (100, 100, ?, 'IB Biology HL', 'Biology', 'HL', "
        "'DEMOJOIN', ?)",
        (teacher_uid, now.isoformat()),
    )

    # Add students to the class
    for sid in student_ids:
        db.execute(
            "INSERT OR IGNORE INTO class_members (class_id, user_id, joined_at) "
            "VALUES (100, ?, ?)",
            (sid, now.isoformat()),
        )

    db.commit()

    return {
        "students_created": len(student_ids),
        "teacher_id": teacher_uid,
        "grades_seeded": grade_count,
        "class_id": 100,
    }


def clear_demo(db, start_uid: int = 200) -> None:
    """Remove all demo data."""
    end_uid = start_uid + len(DEMO_STUDENTS) + 1
    uids = list(range(start_uid, end_uid))
    placeholders = ",".join("?" * len(uids))

    for table in ("grades", "activity_log", "flashcards", "gamification",
                   "user_subjects", "class_members", "push_subscriptions"):
        db.execute(f"DELETE FROM {table} WHERE user_id IN ({placeholders})", uids)

    db.execute(f"DELETE FROM users WHERE id IN ({placeholders})", uids)
    db.execute("DELETE FROM classes WHERE id = 100")
    db.execute("DELETE FROM schools WHERE id = 100")
    db.commit()


if __name__ == "__main__":
    from app import create_app
    from database import get_db

    app = create_app()
    with app.app_context():
        db = get_db()
        if "--reset" in sys.argv:
            clear_demo(db)
            print("[Seed] Demo data cleared.")
        result = seed(db)
        print(f"[Seed] Done: {result}")
