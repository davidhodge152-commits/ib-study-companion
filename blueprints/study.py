"""Core study routes — study page, generate questions, grade, extract-answer, hint, difficulty."""

from __future__ import annotations

import os
from pathlib import Path

from flask import Blueprint, jsonify, redirect, render_template, request, session as flask_session, url_for
from flask_login import current_user, login_required

from helpers import (
    current_user_id,
    login_or_guest,
    generate_recommendation,
    _command_term_alignment,
)
from extensions import EngineManager
from profile import GradeDetailEntry, XP_AWARDS, BADGE_DEFINITIONS
from db_stores import (
    ActivityLogDB,
    FlashcardDeckDB,
    GamificationProfileDB,
    GradeDetailLogDB,
    MisconceptionLogDB,
    ReviewScheduleDB,
    StudentProfileDB,
    TopicProgressStoreDB,
)
from subject_config import get_subject_config, get_syllabus_topics

bp = Blueprint("study", __name__)


@bp.route("/study")
@login_required
def study():
    uid = current_user_id()
    profile = StudentProfileDB.load(uid)
    if not profile:
        return redirect(url_for("core.onboarding"))

    grade_log = GradeDetailLogDB(uid)
    recommendation = generate_recommendation(profile, grade_log)

    return render_template("study.html", profile=profile, recommendation=recommendation)


@bp.route("/api/study/generate", methods=["POST"])
@login_or_guest
def api_study_generate():
    is_guest = flask_session.get("guest") and not current_user.is_authenticated
    data = request.get_json()
    subject = data.get("subject", "")
    topic = data.get("topic", "")
    count = int(data.get("count", 3))
    level = data.get("level", "HL")
    mode = data.get("mode", "smart")
    style = data.get("style", "mixed")

    uid = current_user_id() if not is_guest else None
    profile = StudentProfileDB.load(uid) if uid else None

    if mode == "smart" and not subject and profile:
        grade_log = GradeDetailLogDB(uid)
        rec = generate_recommendation(profile, grade_log)
        if rec["subject"]:
            subject = rec["subject"]
            for s in profile.subjects:
                if s.name == subject:
                    level = s.level
                    break

    if not subject or not topic:
        return jsonify({"error": "Subject and topic are required"}), 400

    exam_paper_info = None
    if mode == "exam_sim":
        count = max(count, 5)
        exam_config = get_subject_config(subject)
        if exam_config:
            papers = exam_config.assessment_hl if level == "HL" else exam_config.assessment_sl
            if papers:
                exam_paper_info = {
                    "papers": [
                        {
                            "name": p.name,
                            "description": p.description,
                            "duration_minutes": p.duration_minutes,
                            "marks": p.marks,
                            "weighting_pct": p.weighting_pct,
                        }
                        for p in papers if not p.hl_only or level == "HL"
                    ],
                    "total_duration": sum(p.duration_minutes for p in papers if not p.hl_only or level == "HL"),
                    "total_marks": sum(p.marks for p in papers if not p.hl_only or level == "HL"),
                }

    try:
        engine = EngineManager.get_engine()
        subject_key = subject.lower().split(":")[0].strip().replace(" ", "_")

        config = get_subject_config(subject)

        difficulty_level = 0
        try:
            if not uid:
                raise ValueError("guest")
            grade_log = GradeDetailLogDB(uid)
            recent_entries = grade_log.by_subject(subject_key)
            if len(recent_entries) >= 3:
                recent_slice = recent_entries[-10:]
                avg_grade = sum(e.grade for e in recent_slice) / len(recent_slice)
                if avg_grade >= 6:
                    difficulty_level = 5
                elif avg_grade >= 5:
                    difficulty_level = 4
                elif avg_grade >= 4:
                    difficulty_level = 3
                elif avg_grade >= 3:
                    difficulty_level = 2
                else:
                    difficulty_level = 1
        except Exception:
            pass

        questions = engine.generate_questions(
            subject=subject_key,
            topic=topic,
            level=level,
            count=count,
            style=style,
            subject_config=config,
            difficulty_level=difficulty_level,
        )

        result = {
            "questions": [
                {
                    "question_text": q.question_text,
                    "command_term": q.command_term,
                    "marks": q.marks,
                    "topic": q.topic,
                    "model_answer": q.model_answer,
                }
                for q in questions
            ]
        }
        if exam_paper_info:
            result["exam_paper_info"] = exam_paper_info

        if is_guest:
            flask_session["guest_questions"] = flask_session.get("guest_questions", 0) + 1
            result["guest_questions_used"] = flask_session["guest_questions"]
            result["guest_questions_limit"] = 3

        return jsonify(result)
    except FileNotFoundError:
        return jsonify({"error": "No documents ingested yet. Upload some PDFs first."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/study/grade", methods=["POST"])
@login_or_guest
def api_study_grade():
    is_guest = flask_session.get("guest") and not current_user.is_authenticated
    data = request.get_json()
    question = data.get("question", "")
    answer = data.get("answer", "")
    subject = data.get("subject", "")
    marks = int(data.get("marks", 4))
    command_term = data.get("command_term", "")
    level = data.get("level", "HL")
    topic = data.get("topic", "")

    if not question or not answer:
        return jsonify({"error": "Question and answer are required"}), 400

    try:
        grader = EngineManager.get_grader()
        subject_key = subject.lower().split(":")[0].strip().replace(" ", "_")

        result = grader.grade(
            question=question,
            answer=answer,
            subject=subject_key,
            marks=marks,
            command_term=command_term,
            subject_display=subject,
        )

        if is_guest:
            return jsonify({
                "mark_earned": result.mark_earned,
                "mark_total": result.mark_total,
                "grade": result.grade,
                "percentage": result.percentage,
                "strengths": result.strengths,
                "improvements": result.improvements,
                "examiner_tip": result.examiner_tip,
                "full_commentary": result.full_commentary,
                "model_answer": result.model_answer,
                "guest_questions_used": flask_session.get("guest_questions", 0),
                "guest_questions_limit": 3,
            })

        uid = current_user_id()

        grade_log = GradeDetailLogDB(uid)
        detail_entry = GradeDetailEntry(
            subject=subject_key,
            subject_display=subject,
            level=level,
            command_term=command_term,
            grade=result.grade,
            percentage=result.percentage,
            mark_earned=result.mark_earned,
            mark_total=result.mark_total,
            strengths=result.strengths,
            improvements=result.improvements,
            examiner_tip=result.examiner_tip,
            topic=topic,
        )
        grade_log.add(detail_entry)

        activity_log = ActivityLogDB(uid)
        activity_log.record(subject, result.grade, result.percentage)

        if topic:
            tp_store = TopicProgressStoreDB(uid)
            topics = get_syllabus_topics(subject)
            topic_id = ""
            for t in topics:
                if topic.lower() in t.name.lower() or t.name.lower() in topic.lower():
                    topic_id = t.id
                    break
                for st in t.subtopics:
                    if topic.lower() in st.lower() or st.lower() in topic.lower():
                        topic_id = t.id
                        break
                if topic_id:
                    break
            if topic_id:
                tp_store.record(subject, topic_id, topic, result.percentage)

        review_sched = ReviewScheduleDB(uid)
        review_sched.record_review(subject, topic or "general", command_term or "general", result.grade)

        gam = GamificationProfileDB(uid)
        xp_earned = XP_AWARDS["answer_question"]
        if result.grade >= 7:
            xp_earned += XP_AWARDS["grade_7_bonus"]
        elif result.grade >= 5:
            xp_earned += XP_AWARDS["grade_5_bonus"]
        xp_result = gam.award_xp(xp_earned, "answer_question")

        gam.total_questions_answered += 1
        if subject not in gam.subjects_practiced:
            practiced = gam.subjects_practiced
            practiced.append(subject)
            gam.subjects_practiced = practiced
        gam.update_streak(activity_log)

        profile_for_badges = StudentProfileDB.load(uid)
        subjects_count = len(profile_for_badges.subjects) if profile_for_badges else 0
        new_badges = gam.check_badges(
            grade=result.grade,
            subjects_count=subjects_count,
        )
        gam.save()

        fc_deck = FlashcardDeckDB(uid)
        model_answer_text = result.model_answer if hasattr(result, 'model_answer') else ""
        auto_fc = fc_deck.auto_create_from_grade(
            question=question, model_answer=model_answer_text,
            subject=subject, topic=topic, percentage=result.percentage,
        )

        misc_log = MisconceptionLogDB(uid)
        detected_misconceptions = misc_log.scan_improvements(result.improvements, subject)

        profile = StudentProfileDB.load(uid)
        target_grade = 5
        target_pct = 60
        grade_gap = 0
        if profile:
            for s in profile.subjects:
                if s.name == subject:
                    target_grade = s.target_grade
                    break
            grade_pct_map = {7: 80, 6: 70, 5: 60, 4: 50, 3: 40, 2: 25, 1: 0}
            target_pct = grade_pct_map.get(target_grade, 60)
            grade_gap = target_pct - result.percentage

        ct_check = _command_term_alignment(command_term, result.improvements)

        if result.percentage < 40 and topic:
            try:
                from sos_detector import SOSDetector
                SOSDetector(uid).check_for_sos()
            except Exception:
                pass

        return jsonify({
            "mark_earned": result.mark_earned,
            "mark_total": result.mark_total,
            "grade": result.grade,
            "percentage": result.percentage,
            "strengths": result.strengths,
            "improvements": result.improvements,
            "examiner_tip": result.examiner_tip,
            "full_commentary": result.full_commentary,
            "target_grade": target_grade,
            "target_pct": target_pct,
            "grade_gap": grade_gap,
            "command_term_check": ct_check,
            "model_answer": result.model_answer,
            "xp_earned": xp_earned,
            "total_xp": gam.total_xp,
            "level": gam.level,
            "streak": gam.current_streak,
            "new_badges": [BADGE_DEFINITIONS.get(b, {"name": b}) for b in new_badges],
            "daily_goal_pct": gam.daily_goal_pct,
            "flashcard_created": auto_fc is not None,
            "misconceptions_detected": detected_misconceptions,
        })
    except FileNotFoundError:
        return jsonify({"error": "No documents ingested yet. Upload some PDFs first."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/study/extract-answer", methods=["POST"])
@login_required
def api_study_extract_answer():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    filename_lower = file.filename.lower()
    allowed_ext = (".jpg", ".jpeg", ".png", ".heic", ".webp", ".pdf")
    if not any(filename_lower.endswith(ext) for ext in allowed_ext):
        return jsonify({"error": "Unsupported file type. Use JPEG, PNG, HEIC, WebP, or PDF."}), 400

    try:
        file_bytes = file.read()

        if filename_lower.endswith(".pdf"):
            from ingest import extract_text
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = Path(tmp.name)
            try:
                text = extract_text(tmp_path)
            finally:
                tmp_path.unlink(missing_ok=True)
        else:
            import google.generativeai as genai
            api_key = os.environ.get("GOOGLE_API_KEY")
            if not api_key:
                return jsonify({"error": "GOOGLE_API_KEY not configured"}), 500
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.0-flash")

            mime_map = {
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png", ".heic": "image/heic",
                ".webp": "image/webp",
            }
            ext = "." + filename_lower.rsplit(".", 1)[-1]
            mime_type = mime_map.get(ext, "image/jpeg")

            response = model.generate_content([
                "Read and transcribe ALL the text in this image exactly as written. "
                "This is a student's answer to a study question. "
                "Preserve paragraph structure and any bullet points. "
                "Return ONLY the transcribed text, nothing else.",
                {"mime_type": mime_type, "data": file_bytes},
            ])
            text = response.text

        if not text or not text.strip():
            return jsonify({"error": "Could not extract any text from the file."}), 400

        return jsonify({"text": text.strip()})

    except Exception as e:
        return jsonify({"error": f"Extraction failed: {e}"}), 500


@bp.route("/api/study/hint", methods=["POST"])
@login_required
def api_study_hint():
    data = request.get_json()
    question = data.get("question", "")
    command_term = data.get("command_term", "")
    hint_level = int(data.get("hint_level", 1))

    if not question:
        return jsonify({"error": "question is required"}), 400

    try:
        engine = EngineManager.get_engine()

        if hint_level == 1:
            hint_instruction = "Ask 1-2 guiding questions that nudge the student toward the right direction. Be vague — don't give away the answer."
        elif hint_level == 2:
            hint_instruction = "Give a more specific direction. Mention the key concept area they should think about, or provide a framework to structure their answer."
        else:
            hint_instruction = "Provide a partial framework or structure for the answer. Mention key terms they should use, but don't write the full answer."

        prompt = f"""You are a Socratic IB tutor. A student needs help with this question:

QUESTION: {question}
COMMAND TERM: {command_term}

{hint_instruction}

DO NOT give the answer. Guide them to discover it themselves.
Keep your hint to 2-3 sentences maximum."""

        hint_text = engine.ask(prompt)
        return jsonify({"hint": hint_text, "hint_level": hint_level})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/difficulty/<subject>")
@login_required
def api_difficulty(subject):
    """Return the computed difficulty level for a subject based on recent grades."""
    uid = current_user_id()
    grade_log = GradeDetailLogDB(uid)
    entries = grade_log.by_subject(subject)

    if len(entries) < 3:
        return jsonify({"level": 3, "label": "Medium", "description": "Default difficulty — not enough data yet"})

    recent = entries[-10:]
    avg = sum(e.grade for e in recent) / len(recent)

    if avg >= 6:
        level, label = 5, "Synthesis & Evaluation"
    elif avg >= 5:
        level, label = 4, "Analysis & Comparison"
    elif avg >= 4:
        level, label = 3, "Explanation & Application"
    elif avg >= 3:
        level, label = 2, "Description & Outline"
    else:
        level, label = 1, "Recall & Definitions"

    command_term_map = {
        1: ["Define", "State", "List", "Identify"],
        2: ["Describe", "Outline", "Distinguish"],
        3: ["Explain", "Suggest", "Annotate"],
        4: ["Analyse", "Compare", "Contrast"],
        5: ["Evaluate", "Discuss", "To what extent", "Examine"],
    }

    return jsonify({
        "level": level,
        "label": label,
        "avg_grade": round(avg, 1),
        "command_terms": command_term_map.get(level, []),
        "entries_used": len(recent),
    })


@bp.route("/api/study/review-calendar")
@login_required
def api_review_calendar():
    """Return items due for review grouped by date for the next 30 days."""
    from datetime import datetime, timedelta
    from database import get_db

    uid = current_user_id()
    db = get_db()
    today = datetime.now().date()
    end_date = today + timedelta(days=30)

    # Spaced repetition review schedule items
    schedule_rows = db.execute(
        "SELECT subject, topic, command_term, next_review, interval_days "
        "FROM review_schedule WHERE user_id = ? AND next_review != '' "
        "ORDER BY next_review",
        (uid,),
    ).fetchall()

    # Flashcards due for review
    flashcard_rows = db.execute(
        "SELECT subject, topic, front, next_review "
        "FROM flashcards WHERE user_id = ? AND next_review != '' "
        "ORDER BY next_review",
        (uid,),
    ).fetchall()

    calendar = {}
    for row in schedule_rows:
        try:
            d = datetime.fromisoformat(row["next_review"]).date()
        except (ValueError, TypeError):
            continue
        if today <= d <= end_date:
            key = d.isoformat()
            calendar.setdefault(key, []).append({
                "type": "review",
                "subject": row["subject"],
                "topic": row["topic"],
                "command_term": row["command_term"],
                "interval_days": row["interval_days"],
            })

    for row in flashcard_rows:
        try:
            d = datetime.fromisoformat(row["next_review"]).date()
        except (ValueError, TypeError):
            continue
        if today <= d <= end_date:
            key = d.isoformat()
            calendar.setdefault(key, []).append({
                "type": "flashcard",
                "subject": row["subject"],
                "topic": row["topic"],
                "front": row["front"][:80],
            })

    return jsonify({"calendar": calendar})


@bp.route("/api/study/weak-topics")
@login_required
def api_weak_topics():
    """Return topics where the student is struggling (low avg or few attempts)."""
    from database import get_db

    uid = current_user_id()
    db = get_db()

    # Topics with low average or few attempts
    rows = db.execute(
        "SELECT subject, topic_id, subtopic, attempts, avg_percentage, last_practiced "
        "FROM topic_progress WHERE user_id = ? AND (avg_percentage < 50 OR attempts < 3) "
        "ORDER BY avg_percentage ASC, attempts ASC LIMIT 20",
        (uid,),
    ).fetchall()

    weak_topics = [
        {
            "subject": r["subject"],
            "topic_id": r["topic_id"],
            "subtopic": r["subtopic"],
            "attempts": r["attempts"],
            "avg_percentage": r["avg_percentage"],
            "last_practiced": r["last_practiced"],
        }
        for r in rows
    ]

    # Also include active SOS alerts
    sos_rows = db.execute(
        "SELECT subject, topic, command_term, failure_count, avg_percentage "
        "FROM sos_alerts WHERE user_id = ? AND status = 'active' "
        "ORDER BY avg_percentage ASC",
        (uid,),
    ).fetchall()

    sos_alerts = [
        {
            "subject": r["subject"],
            "topic": r["topic"],
            "command_term": r["command_term"],
            "failure_count": r["failure_count"],
            "avg_percentage": r["avg_percentage"],
        }
        for r in sos_rows
    ]

    return jsonify({"weak_topics": weak_topics, "sos_alerts": sos_alerts})


@bp.route("/api/study/exam-history")
@login_required
def api_exam_history():
    """Return exam simulation history with per-session stats."""
    import json as _json
    from database import get_db

    uid = current_user_id()
    db = get_db()

    rows = db.execute(
        "SELECT id, subject, level, paper_number, duration_minutes, "
        "started_at, completed_at, total_marks, earned_marks, grade, questions, answers "
        "FROM exam_sessions WHERE user_id = ? ORDER BY started_at DESC LIMIT 20",
        (uid,),
    ).fetchall()

    sessions = []
    for r in rows:
        percentage = round(r["earned_marks"] / r["total_marks"] * 100, 1) if r["total_marks"] > 0 else 0

        # Parse questions for command term breakdown
        command_term_stats = {}
        try:
            questions = _json.loads(r["questions"]) if r["questions"] else []
            answers = _json.loads(r["answers"]) if r["answers"] else []
            for i, q in enumerate(questions):
                ct = q.get("command_term", "Unknown")
                if ct not in command_term_stats:
                    command_term_stats[ct] = {"total": 0, "earned": 0, "count": 0}
                command_term_stats[ct]["count"] += 1
                mark_total = q.get("marks", 0)
                command_term_stats[ct]["total"] += mark_total
                if i < len(answers):
                    command_term_stats[ct]["earned"] += answers[i].get("marks_earned", 0)
        except (ValueError, TypeError):
            pass

        sessions.append({
            "id": r["id"],
            "subject": r["subject"],
            "level": r["level"],
            "paper_number": r["paper_number"],
            "duration_minutes": r["duration_minutes"],
            "started_at": r["started_at"],
            "completed_at": r["completed_at"],
            "total_marks": r["total_marks"],
            "earned_marks": r["earned_marks"],
            "grade": r["grade"],
            "percentage": percentage,
            "command_term_breakdown": command_term_stats,
        })

    return jsonify({"sessions": sessions})
