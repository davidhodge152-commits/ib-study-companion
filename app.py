"""
IB Study Companion — Flask Web Application

Target-driven study platform with IB lifecycle management, parent portal,
spaced repetition, and study planner.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, date, timedelta
from pathlib import Path

from flask import (
    Flask,
    Response,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required, current_user

from profile import (
    IB_SUBJECTS,
    SubjectEntry,
    XP_AWARDS,
    BADGE_DEFINITIONS,
    GradeDetailEntry,
    Flashcard,
    Notification,
    StudyTask,
    DailyPlan,
    MockExamReport,
    MISCONCEPTION_PATTERNS,
)
from db_stores import (
    StudentProfileDB,
    GradeDetailLogDB,
    TopicProgressStoreDB,
    ActivityLogDB,
    ReviewScheduleDB,
    GamificationProfileDB,
    FlashcardDeckDB,
    MisconceptionLogDB,
    MockExamReportStoreDB,
    NotificationStoreDB,
    SharedQuestionStoreDB,
    StudyPlanDB,
    WritingProfileDB,
    ParentConfigDB,
    IBLifecycleDB,
    GradeHistoryDB,
    UploadStoreDB,
    # New stores (Steps 3-11)
    SchoolStoreDB,
    ClassStoreDB,
    AssignmentStoreDB,
    StudyGroupStoreDB,
    ChallengeStoreDB,
    LeaderboardStoreDB,
    PushSubscriptionStoreDB,
    CommunityPaperStoreDB,
    StudentAbilityStoreDB,
    ExamSessionStoreDB,
    TutorConversationStoreDB,
)
import database
from auth import auth_bp, login_manager
from subject_config import (
    SUBJECT_CONFIG,
    SYLLABUS_TOPICS,
    get_subject_config,
    get_syllabus_topics,
)
from lifecycle import CASReflection, CAS_LEARNING_OUTCOMES

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def current_user_id() -> int:
    """Return the current authenticated user's ID, or 1 as fallback."""
    if current_user.is_authenticated:
        return current_user.id
    return 1


def login_or_guest(f):
    """Allow both authenticated users and guest sessions."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import session as flask_session
        if current_user.is_authenticated or flask_session.get("guest"):
            return f(*args, **kwargs)
        return login_manager.unauthorized()
    return decorated


def create_app(test_config=None):
    app = Flask(__name__)
    from flask import session as flask_session

    # Load config
    if test_config is not None:
        app.config.update(test_config)
    else:
        from config import config_by_name
        env = os.environ.get("FLASK_ENV", "development")
        app.config.from_object(config_by_name.get(env, config_by_name["development"]))

    app.secret_key = app.config.get("SECRET_KEY", os.environ.get('SECRET_KEY', 'dev-key-change-in-production'))

    # CSRF protection
    try:
        from flask_wtf.csrf import CSRFProtect
        csrf = CSRFProtect(app)
    except ImportError:
        csrf = None

    # i18n with Flask-Babel
    try:
        from flask_babel import Babel
        babel = Babel()

        def get_locale():
            # Check user preference first, then Accept-Language header
            if current_user.is_authenticated:
                try:
                    from database import get_db
                    db = get_db()
                    row = db.execute("SELECT locale FROM users WHERE id = ?",
                                     (current_user.id,)).fetchone()
                    if row and row["locale"]:
                        return row["locale"]
                except Exception:
                    pass
            return request.accept_languages.best_match(["en", "fr", "es"], default="en")

        babel.init_app(app, locale_selector=get_locale)
    except ImportError:
        pass

    # Static file serving for production (whitenoise)
    try:
        from whitenoise import WhiteNoise
        app.wsgi_app = WhiteNoise(app.wsgi_app, root=os.path.join(app.root_path, 'static'), prefix='static/')
    except ImportError:
        pass

    # Register database teardown
    database.init_app(app)

    # Register auth blueprint and login manager
    app.register_blueprint(auth_bp)
    login_manager.init_app(app)

    # ── Lazy engine singletons (closure-local) ────────────────────
    _engine = None
    _grader = None

    def get_engine():
        nonlocal _engine
        if _engine is None:
            from rag_engine import RAGEngine
            _engine = RAGEngine()
        return _engine

    def get_grader():
        nonlocal _grader
        if _grader is None:
            from grader import IBGrader
            _grader = IBGrader(get_engine())
        return _grader

    # ── Intelligence helpers (no AI calls) ─────────────────────────

    COMMAND_TERM_THRESHOLDS = {
        "Define": 85, "State": 85, "List": 85, "Identify": 80,
        "Describe": 70, "Outline": 70, "Distinguish": 70,
        "Explain": 65, "Suggest": 65, "Annotate": 70,
        "Analyse": 60, "Compare": 60, "Compare and contrast": 60, "Contrast": 60,
        "Evaluate": 55, "Discuss": 55, "To what extent": 55, "Justify": 55, "Examine": 55,
    }

    def generate_recommendation(profile, grade_log):
        """Deterministic recommendation: biggest gap -> weakest command term -> action."""
        gaps = profile.compute_gaps(grade_log)
        ct_stats = grade_log.command_term_stats()

        target_subject = None
        for g in gaps:
            if g["status"] in ("behind", "close"):
                target_subject = g
                break

        if not target_subject:
            for g in gaps:
                if g["status"] == "no_data":
                    target_subject = g
                    break
            if not target_subject and gaps:
                target_subject = gaps[0]

        if not target_subject:
            return {
                "subject": "",
                "reason": "Add subjects to your profile to get recommendations.",
                "command_term_focus": "",
                "priority": "low",
            }

        weakest_ct = ""
        weakest_ct_pct = 100
        for ct, stats in ct_stats.items():
            if stats["count"] >= 1 and stats["avg_percentage"] < weakest_ct_pct:
                weakest_ct = ct
                weakest_ct_pct = stats["avg_percentage"]

        if target_subject["status"] == "no_data":
            reason = f"Start practicing {target_subject['subject']} — no data yet."
            priority = "medium"
        elif target_subject["status"] == "behind":
            reason = (
                f"{target_subject['subject']} {target_subject['level']} is your biggest gap "
                f"({target_subject['gap']:+d} grade{'s' if abs(target_subject['gap']) != 1 else ''} "
                f"from target {target_subject['target']})."
            )
            priority = "high"
        else:
            reason = (
                f"{target_subject['subject']} {target_subject['level']} is close to target "
                f"({target_subject['gap']:+d})."
            )
            priority = "medium"

        # Enrich with syllabus coverage data
        tp_store = TopicProgressStoreDB(current_user_id())
        topics = get_syllabus_topics(target_subject["subject"])
        if topics:
            tp = tp_store.get(target_subject["subject"])
            coverage = tp.overall_coverage(topics)
            if coverage < 100:
                # Find first uncovered topic
                for t in topics:
                    if not tp.topics.get(t.id):
                        reason += f" You've covered {coverage:.0f}% of the syllabus — try {t.name} next."
                        break

        ct_detail = ""
        if weakest_ct and weakest_ct_pct < 70:
            ct_detail = f" Your weakest command term is {weakest_ct} ({weakest_ct_pct:.0f}% avg)."
            reason += ct_detail

        return {
            "subject": target_subject["subject"],
            "level": target_subject["level"],
            "reason": reason,
            "command_term_focus": weakest_ct if weakest_ct_pct < 70 else "",
            "priority": priority,
        }

    def _command_term_alignment(command_term: str, improvements: list[str]) -> str:
        if not command_term or not improvements:
            return ""

        ct_lower = command_term.lower()
        checks = {
            "evaluate": ["one-sided", "counter-argument", "both sides", "balanced", "limitation"],
            "discuss": ["one-sided", "counter-argument", "both sides", "balanced"],
            "analyse": ["break down", "component", "relationship", "cause"],
            "explain": ["reason", "mechanism", "cause", "why"],
            "compare": ["similarit", "difference", "contrast", "both"],
            "define": ["definition", "precise", "terminology"],
        }

        keywords = checks.get(ct_lower, [])
        if not keywords:
            return ""

        feedback_text = " ".join(improvements).lower()
        for kw in keywords:
            if kw in feedback_text:
                return f"The examiner noted issues related to '{command_term}' expectations — make sure you understand what this command term requires."

        return ""

    def _generate_text_insights(
        grade_log,
        profile,
        ct_stats: dict,
        gaps: list[dict],
    ) -> list[dict]:
        insights = []

        for g in gaps:
            if g["status"] == "behind":
                insights.append({
                    "severity": "red",
                    "title": f"{g['subject']} {g['level']} needs attention",
                    "body": f"You're predicted a {g['predicted']}, but your target is {g['target']} ({g['gap']:+d} gap).",
                    "action": f"Focus your next study sessions on {g['subject']}.",
                })
                break

        weakest_ct = None
        for ct, stats in sorted(ct_stats.items(), key=lambda x: x[1]["avg_percentage"]):
            if stats["count"] >= 2 and stats["avg_percentage"] < 65:
                weakest_ct = (ct, stats)
                break

        if weakest_ct:
            ct_name, ct_data = weakest_ct
            insights.append({
                "severity": "yellow",
                "title": f"Weak on '{ct_name}' questions",
                "body": f"Average {ct_data['avg_percentage']}% across {ct_data['count']} attempts.",
                "action": f"Use Command Term Trainer to practice '{ct_name}' questions.",
            })

        entries = grade_log.entries
        if len(entries) >= 4:
            recent = entries[-4:]
            older = entries[-8:-4] if len(entries) >= 8 else entries[:4]
            recent_avg = sum(e.percentage for e in recent) / len(recent)
            older_avg = sum(e.percentage for e in older) / len(older)
            diff = recent_avg - older_avg

            if diff > 5:
                insights.append({
                    "severity": "green",
                    "title": "Performance is improving",
                    "body": f"Your recent average is {recent_avg:.0f}%, up from {older_avg:.0f}% (+{diff:.0f}%).",
                    "action": "Keep up the momentum!",
                })
            elif diff < -5:
                insights.append({
                    "severity": "red",
                    "title": "Performance is declining",
                    "body": f"Your recent average is {recent_avg:.0f}%, down from {older_avg:.0f}% ({diff:.0f}%).",
                    "action": "Consider reviewing fundamentals before attempting harder questions.",
                })

        if len(insights) < 3 and len(entries) > 0:
            total = len(entries)
            avg_pct = sum(e.percentage for e in entries) / total
            insights.append({
                "severity": "blue",
                "title": f"{total} answers graded so far",
                "body": f"Overall average: {avg_pct:.0f}%.",
                "action": "Keep practicing to build a clearer picture of your strengths.",
            })

        return insights[:3]

    def _analyze_writing_style(text: str) -> None:
        engine = get_engine()
        prompt = f"""Analyze this student's writing from an IB exam. Identify:

1. VERBOSITY: Are they concise or verbose? Do they tend to over-explain or under-explain?
2. TERMINOLOGY: How well do they use subject-specific terminology? Do they define terms?
3. ARGUMENT_STRUCTURE: How do they organize arguments? Do they use clear topic sentences? Do they provide balanced evaluations?
4. PATTERNS: List 3-5 recurring patterns (good or bad) in their writing.
5. SUMMARY: A 2-3 sentence overall profile of this student's exam writing style.

Format your response EXACTLY as:
VERBOSITY: [description]
TERMINOLOGY: [description]
ARGUMENT_STRUCTURE: [description]
PATTERNS:
- [pattern 1]
- [pattern 2]
- [pattern 3]
SUMMARY: [2-3 sentences]

Student's exam text:
{text[:8000]}"""

        raw = engine.ask(prompt)

        uid = current_user_id()
        wp_db = WritingProfileDB(uid)
        existing = wp_db.load()

        verbosity = ""
        terminology_usage = ""
        argument_structure = ""
        summary = ""
        common_patterns = []
        analyzed_count = (existing["analyzed_count"] if existing else 0)

        for line in raw.splitlines():
            stripped = line.strip()
            if stripped.startswith("VERBOSITY:"):
                verbosity = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("TERMINOLOGY:"):
                terminology_usage = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("ARGUMENT_STRUCTURE:"):
                argument_structure = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("SUMMARY:"):
                summary = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("- ") and verbosity:
                common_patterns.append(stripped[2:])

        analyzed_count += 1
        wp_db.save(
            verbosity=verbosity,
            terminology_usage=terminology_usage,
            argument_structure=argument_structure,
            common_patterns=common_patterns,
            summary=summary,
            analyzed_count=analyzed_count,
            last_updated=datetime.now().isoformat(),
        )

    def _last_active_date(activity_log) -> date:
        if not activity_log.entries:
            return date.today() - timedelta(days=30)
        dates = [e.date for e in activity_log.entries]
        return date.fromisoformat(max(dates))

    def generate_pending_notifications(user_id: int) -> list[Notification]:
        """Check all notification triggers and create new notifications if needed."""
        store = NotificationStoreDB(user_id)
        new_notifications: list[Notification] = []
        today = date.today().isoformat()

        # 1. Flashcards due
        fc_deck = FlashcardDeckDB(user_id)
        due_count = fc_deck.due_count()
        if due_count > 0 and not store.has_today("flashcard_due"):
            notif = Notification(
                id=f"fc_due_{today}",
                type="flashcard_due",
                title=f"{due_count} flashcards due for review",
                body=f"You have {due_count} flashcards waiting. Review them to strengthen your memory.",
                created_at=datetime.now().isoformat(),
                action_url="/flashcards",
                data={"count": due_count},
            )
            store.add(notif)
            new_notifications.append(notif)

        # 2. Streak at risk
        activity_log = ActivityLogDB(user_id)
        gam = GamificationProfileDB(user_id)
        if gam.current_streak > 0:
            active_dates = {e.date for e in activity_log.entries}
            if today not in active_dates and not store.has_today("streak_risk"):
                notif = Notification(
                    id=f"streak_risk_{today}",
                    type="streak_risk",
                    title=f"Your {gam.current_streak}-day streak is at risk!",
                    body="Study today to keep your streak alive.",
                    created_at=datetime.now().isoformat(),
                    action_url="/study",
                    data={"streak": gam.current_streak},
                )
                store.add(notif)
                new_notifications.append(notif)

        # 3. Study plan tasks
        plan_data = StudyPlanDB(user_id).load()
        if plan_data:
            for dp in plan_data["daily_plans"]:
                if dp.date == today:
                    incomplete = sum(1 for t in dp.tasks if not t.completed)
                    if incomplete > 0 and not store.has_today("plan_reminder"):
                        notif = Notification(
                            id=f"plan_{today}",
                            type="plan_reminder",
                            title=f"{incomplete} study tasks for today",
                            body=f"Your study plan has {incomplete} uncompleted tasks.",
                            created_at=datetime.now().isoformat(),
                            action_url="/planner",
                            data={"task_count": incomplete},
                        )
                        store.add(notif)
                        new_notifications.append(notif)
                    break

        return new_notifications

    # ── Page routes ────────────────────────────────────────────────

    @app.route("/")
    @login_required
    def index():
        if not StudentProfileDB.exists(current_user_id()):
            return redirect(url_for("onboarding"))
        return redirect(url_for("dashboard"))

    @app.route("/onboarding")
    @login_required
    def onboarding():
        profile = StudentProfileDB.load(current_user_id())
        return render_template("onboarding.html", ib_subjects=IB_SUBJECTS, profile=profile)

    @app.route("/onboarding", methods=["POST"])
    @login_required
    def onboarding_submit():
        name = request.form.get("name", "").strip()
        exam_session = request.form.get("exam_session", "").strip()
        target_total_points = int(request.form.get("target_total_points", 35))
        target_total_points = max(24, min(45, target_total_points))

        subjects = []
        i = 0
        while True:
            subj_name = request.form.get(f"subject_{i}")
            subj_level = request.form.get(f"level_{i}")
            if subj_name is None:
                break
            if subj_name.strip():
                target_grade = int(request.form.get(f"target_{i}", 5))
                target_grade = max(1, min(7, target_grade))
                subjects.append(SubjectEntry(
                    name=subj_name.strip(),
                    level=subj_level or "HL",
                    target_grade=target_grade,
                ))
            i += 1

        if not name or not subjects:
            return render_template(
                "onboarding.html",
                ib_subjects=IB_SUBJECTS,
                profile=None,
                error="Please enter your name and select at least one subject.",
            )

        uid = current_user_id()
        existing = StudentProfileDB.load(uid)
        if existing:
            existing.save_fields(
                name=name,
                subjects=subjects,
                exam_session=exam_session,
                target_total_points=target_total_points,
            )
        else:
            StudentProfileDB.create(
                name=name,
                subjects=subjects,
                exam_session=exam_session,
                target_total_points=target_total_points,
            )

        # Auto-populate lifecycle IAs from subjects
        lifecycle = IBLifecycleDB(uid)
        lifecycle.init_from_profile([s.name for s in subjects])

        return redirect(url_for("dashboard"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        uid = current_user_id()
        profile = StudentProfileDB.load(uid)
        if not profile:
            return redirect(url_for("onboarding"))

        grade_log = GradeDetailLogDB(uid)
        countdown = profile.exam_countdown()
        gaps = profile.compute_gaps(grade_log)
        predicted_total = profile.compute_predicted_total(grade_log)
        recommendation = generate_recommendation(profile, grade_log)

        recent = []
        for e in grade_log.recent(5):
            recent.append({
                "subject": e.subject_display,
                "command_term": e.command_term,
                "grade": e.grade,
                "percentage": e.percentage,
                "mark": f"{e.mark_earned}/{e.mark_total}",
                "timestamp": e.timestamp,
            })

        # Syllabus coverage per subject
        tp_store = TopicProgressStoreDB(uid)
        coverage_data = {}
        for s in profile.subjects:
            topics = get_syllabus_topics(s.name)
            if topics:
                tp = tp_store.get(s.name)
                coverage_data[s.name] = tp.overall_coverage(topics)

        # Spaced repetition due items
        review_sched = ReviewScheduleDB(uid)
        review_due = len(review_sched.due_today())

        # Lifecycle summary
        lifecycle = IBLifecycleDB(uid)
        lifecycle_summary = lifecycle.summary()

        # Gamification
        gam = GamificationProfileDB(uid)
        activity_log = ActivityLogDB(uid)
        gam.update_streak(activity_log)

        # Activity heatmap
        heatmap = activity_log.daily_heatmap(90)

        # Flashcard due count
        fc_deck = FlashcardDeckDB(uid)
        flashcard_due = fc_deck.due_count()

        # Today's tasks from study plan
        plan_data = StudyPlanDB(uid).load()
        today_tasks = []
        if plan_data:
            today_str = date.today().isoformat()
            for dp in plan_data["daily_plans"]:
                if dp.date == today_str:
                    for i, t in enumerate(dp.tasks):
                        today_tasks.append({
                            "subject": t.subject,
                            "topic": t.topic,
                            "task_type": t.task_type,
                            "duration_minutes": t.duration_minutes,
                            "priority": t.priority,
                            "completed": t.completed,
                            "index": i,
                            "date": dp.date,
                        })

        # Predicted grades with confidence intervals
        subject_predictions = []
        for s in profile.subjects:
            entries = grade_log.by_subject(s.name)
            if len(entries) >= 3:
                grades = [e.grade for e in entries]
                # Recent-weighted: last entries count more
                recent_grades = grades[-10:]
                mean_grade = sum(recent_grades) / len(recent_grades)
                variance = sum((g - mean_grade) ** 2 for g in recent_grades) / len(recent_grades)
                std_dev = variance ** 0.5
                confidence = "high" if len(entries) >= 15 and std_dev < 1 else "medium" if len(entries) >= 8 else "low"
                low = max(1, round(mean_grade - std_dev))
                high = min(7, round(mean_grade + std_dev))
                predicted = round(mean_grade)

                # Trend detection
                if len(grades) >= 6:
                    first_half = sum(grades[:len(grades)//2]) / (len(grades)//2)
                    second_half = sum(grades[len(grades)//2:]) / (len(grades) - len(grades)//2)
                    if second_half - first_half > 0.5:
                        trend = "improving"
                    elif first_half - second_half > 0.5:
                        trend = "declining"
                    else:
                        trend = "stable"
                else:
                    trend = "stable"
            elif len(entries) > 0:
                grades = [e.grade for e in entries]
                mean_grade = sum(grades) / len(grades)
                predicted = round(mean_grade)
                low = max(1, predicted - 1)
                high = min(7, predicted + 1)
                confidence = "low"
                trend = "stable"
            else:
                predicted = 0
                low = 0
                high = 0
                confidence = "none"
                trend = "stable"

            topics = get_syllabus_topics(s.name)
            coverage_pct = coverage_data.get(s.name, 0)

            subject_predictions.append({
                "subject": s.name,
                "level": s.level,
                "target": s.target_grade,
                "predicted": predicted,
                "low": low,
                "high": high,
                "confidence": confidence,
                "trend": trend,
                "coverage": coverage_pct,
            })

        return render_template(
            "dashboard.html",
            profile=profile,
            countdown=countdown,
            gaps=gaps,
            predicted_total=predicted_total,
            recommendation=recommendation,
            recent=recent,
            coverage_data=coverage_data,
            review_due=review_due,
            lifecycle_summary=lifecycle_summary,
            gam=gam,
            heatmap=heatmap,
            flashcard_due=flashcard_due,
            today_tasks=today_tasks,
            subject_predictions=subject_predictions,
        )

    @app.route("/upload")
    @login_required
    def upload():
        uid = current_user_id()
        profile = StudentProfileDB.load(uid)
        if not profile:
            return redirect(url_for("onboarding"))
        uploads = UploadStoreDB(uid).load()
        return render_template("upload.html", profile=profile, uploads=uploads)

    @app.route("/api/upload", methods=["POST"])
    @login_required
    def api_upload():
        nonlocal _engine, _grader

        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "No filename provided"}), 400

        allowed_ext = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
        ext = Path(file.filename).suffix.lower()
        if ext not in allowed_ext:
            return jsonify({"error": f"Supported formats: PDF, PNG, JPG, WEBP"}), 400

        is_image = ext in {".png", ".jpg", ".jpeg", ".webp"}
        doc_type = request.form.get("doc_type", "notes")

        filename = file.filename
        save_path = DATA_DIR / filename
        if save_path.exists():
            stem = save_path.stem
            suffix = save_path.suffix
            filename = f"{stem}_{uuid.uuid4().hex[:6]}{suffix}"
            save_path = DATA_DIR / filename

        file.save(str(save_path))

        try:
            from ingest import (
                extract_text,
                extract_text_from_image,
                classify_document,
                detect_subject,
                detect_level,
                chunk_text,
                file_hash,
            )
            import chromadb

            text = extract_text_from_image(save_path) if is_image else extract_text(save_path)
            if not text.strip():
                msg = "Could not extract text from image" if is_image else "No extractable text in PDF (scanned?)"
                return jsonify({"error": msg}), 400

            detected_type = doc_type if doc_type != "auto" else classify_document(filename, text)
            subject = detect_subject(filename, text)
            level = detect_level(filename, text)
            chunks = chunk_text(text)
            fhash = file_hash(save_path)
            prefix = f"{save_path.stem}_{fhash}"

            chroma_dir = Path(__file__).parent / "chroma_db"
            client = chromadb.PersistentClient(path=str(chroma_dir))
            collection = client.get_or_create_collection(
                name="ib_documents",
                metadata={"hnsw:space": "cosine"},
            )

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

            collection.add(documents=chunks, ids=ids, metadatas=metadatas)

            _engine = None
            _grader = None

        except Exception as e:
            return jsonify({"error": f"Ingestion failed: {e}"}), 500

        uid = current_user_id()
        upload_entry = {
            "id": uuid.uuid4().hex,
            "filename": filename,
            "doc_type": detected_type,
            "subject": subject,
            "level": level,
            "chunks": len(chunks),
            "uploaded_at": datetime.now().isoformat(),
        }
        UploadStoreDB(uid).add(upload_entry)

        if doc_type == "my_past_exam":
            try:
                _analyze_writing_style(text)
            except Exception:
                pass

        # Award XP for upload
        gam = GamificationProfileDB(uid)
        gam.award_xp(XP_AWARDS["upload_document"], "upload_document")

        return jsonify({
            "success": True,
            "filename": filename,
            "doc_type": detected_type,
            "subject": subject,
            "level": level,
            "chunks": len(chunks),
        })

    @app.route("/documents")
    @login_required
    def documents():
        uid = current_user_id()
        profile = StudentProfileDB.load(uid)
        if not profile:
            return redirect(url_for("onboarding"))

        uploads = UploadStoreDB(uid).load()

        try:
            stats = get_engine().collection_stats()
        except Exception:
            stats = {"count": 0, "subjects": [], "doc_types": [], "sources": []}

        return render_template("documents.html", profile=profile, uploads=uploads, stats=stats)

    @app.route("/api/documents/<doc_id>", methods=["DELETE"])
    @login_required
    def api_delete_document(doc_id):
        nonlocal _engine, _grader

        uid = current_user_id()
        upload_store = UploadStoreDB(uid)
        target = upload_store.delete(doc_id)

        if not target:
            return jsonify({"error": "Document not found"}), 404

        try:
            import chromadb
            chroma_dir = Path(__file__).parent / "chroma_db"
            client = chromadb.PersistentClient(path=str(chroma_dir))
            collection = client.get_collection("ib_documents")
            results = collection.get(where={"source": target["filename"]})
            if results["ids"]:
                collection.delete(ids=results["ids"])
        except Exception:
            pass

        file_path = DATA_DIR / target["filename"]
        if file_path.exists():
            file_path.unlink()

        _engine = None
        _grader = None

        return jsonify({"success": True})

    # ── Study routes ──────────────────────────────────────────────

    @app.route("/study")
    @login_required
    def study():
        uid = current_user_id()
        profile = StudentProfileDB.load(uid)
        if not profile:
            return redirect(url_for("onboarding"))

        grade_log = GradeDetailLogDB(uid)
        recommendation = generate_recommendation(profile, grade_log)

        return render_template("study.html", profile=profile, recommendation=recommendation)

    @app.route("/api/study/generate", methods=["POST"])
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

        # Exam sim: look up paper structure from SubjectConfig
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
            engine = get_engine()
            subject_key = subject.lower().split(":")[0].strip().replace(" ", "_")

            # Pass subject config for subject-aware generation
            config = get_subject_config(subject)

            # Compute adaptive difficulty from recent grades
            difficulty_level = 0  # 0 = use default/mixed
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

            # Increment guest question counter
            if is_guest:
                flask_session["guest_questions"] = flask_session.get("guest_questions", 0) + 1
                result["guest_questions_used"] = flask_session["guest_questions"]
                result["guest_questions_limit"] = 3

            return jsonify(result)
        except FileNotFoundError:
            return jsonify({"error": "No documents ingested yet. Upload some PDFs first."}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/study/grade", methods=["POST"])
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
            grader = get_grader()
            subject_key = subject.lower().split(":")[0].strip().replace(" ", "_")

            result = grader.grade(
                question=question,
                answer=answer,
                subject=subject_key,
                marks=marks,
                command_term=command_term,
                subject_display=subject,
            )

            # Guest mode: return grade result only, skip DB persistence
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

            # Save to GradeDetailLog
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

            # Record activity
            activity_log = ActivityLogDB(uid)
            activity_log.record(subject, result.grade, result.percentage)

            # Record topic progress
            if topic:
                tp_store = TopicProgressStoreDB(uid)
                topics = get_syllabus_topics(subject)
                # Find matching topic_id
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

            # Record spaced repetition
            review_sched = ReviewScheduleDB(uid)
            review_sched.record_review(subject, topic or "general", command_term or "general", result.grade)

            # ── Gamification: XP, badges, flashcards, misconceptions ──
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

            # Check badges
            profile_for_badges = StudentProfileDB.load(uid)
            subjects_count = len(profile_for_badges.subjects) if profile_for_badges else 0
            new_badges = gam.check_badges(
                grade=result.grade,
                subjects_count=subjects_count,
            )
            gam.save()

            # Auto-create flashcard for weak answers
            fc_deck = FlashcardDeckDB(uid)
            model_answer_text = result.model_answer if hasattr(result, 'model_answer') else ""
            auto_fc = fc_deck.auto_create_from_grade(
                question=question, model_answer=model_answer_text,
                subject=subject, topic=topic, percentage=result.percentage,
            )

            # Misconception tracking
            misc_log = MisconceptionLogDB(uid)
            detected_misconceptions = misc_log.scan_improvements(result.improvements, subject)

            # Compute target context
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

            # SOS detection: check if student is struggling
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
                # Gamification data
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

    # ── Answer extraction from image/PDF ──────────────────────────

    @app.route("/api/study/extract-answer", methods=["POST"])
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
                # Use pypdf to extract text from PDF
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
                # Use Gemini vision to read handwritten/typed text from image
                import google.generativeai as genai
                api_key = os.environ.get("GOOGLE_API_KEY")
                if not api_key:
                    return jsonify({"error": "GOOGLE_API_KEY not configured"}), 500
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-2.0-flash")

                # Determine MIME type
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

    # ── Backwards compat redirects ─────────────────────────────────

    @app.route("/quiz")
    @login_required
    def quiz_redirect():
        return redirect(url_for("study"))

    @app.route("/analytics")
    @login_required
    def analytics_redirect():
        return redirect(url_for("insights"))

    # ── Insights routes ──────────────────────────────────────────

    @app.route("/insights")
    @login_required
    def insights():
        uid = current_user_id()
        profile = StudentProfileDB.load(uid)
        if not profile:
            return redirect(url_for("onboarding"))
        return render_template("insights.html", profile=profile)

    @app.route("/api/insights")
    @login_required
    def api_insights():
        try:
            uid = current_user_id()
            grader = get_grader()
            analytics_data = grader.get_analytics()

            # grader.history is now DB-backed; build the history list from GradeHistoryDB
            grade_history = GradeHistoryDB(uid)
            history = []
            for r in grade_history.history:
                history.append({
                    "question": r["question"][:60],
                    "grade": r["grade"],
                    "percentage": r["percentage"],
                    "mark": f"{r['mark_earned']}/{r['mark_total']}",
                    "timestamp": r["timestamp"],
                })
            analytics_data["history"] = history

            grade_log = GradeDetailLogDB(uid)
            profile = StudentProfileDB.load(uid)

            ct_stats = grade_log.command_term_stats()
            analytics_data["command_term_stats"] = ct_stats
            analytics_data["subject_stats"] = grade_log.subject_stats()

            if profile:
                gaps = profile.compute_gaps(grade_log)
                analytics_data["gaps"] = gaps

                total_gap = sum(max(g["gap"], 0) for g in gaps if g["status"] != "no_data")
                allocation = []
                for g in gaps:
                    if g["status"] == "no_data":
                        pct = round(100 / len(gaps)) if gaps else 0
                    elif total_gap > 0:
                        pct = round((max(g["gap"], 0) / total_gap) * 100) if g["gap"] > 0 else 5
                    else:
                        pct = round(100 / len(gaps)) if gaps else 0
                    allocation.append({"subject": g["subject"], "percentage": pct})
                analytics_data["study_allocation"] = allocation

                insights_list = _generate_text_insights(grade_log, profile, ct_stats, gaps)
                analytics_data["insights"] = insights_list

                # Syllabus coverage data
                tp_store = TopicProgressStoreDB(uid)
                coverage = {}
                for s in profile.subjects:
                    topics = get_syllabus_topics(s.name)
                    if topics:
                        tp = tp_store.get(s.name)
                        topic_coverage = []
                        for t in topics:
                            practiced = len(tp.topics.get(t.id, []))
                            total = len(t.subtopics)
                            topic_coverage.append({
                                "id": t.id,
                                "name": t.name,
                                "practiced": practiced,
                                "total": total,
                                "pct": round(practiced / total * 100) if total > 0 else 0,
                                "hl_only": t.hl_only,
                            })
                        coverage[s.name] = {
                            "overall": tp.overall_coverage(topics),
                            "topics": topic_coverage,
                        }
                analytics_data["syllabus_coverage"] = coverage

            wp = WritingProfileDB(uid).load()
            if wp and wp["summary"]:
                analytics_data["writing_profile"] = {
                    "summary": wp["summary"],
                    "verbosity": wp["verbosity"],
                    "terminology_usage": wp["terminology_usage"],
                    "argument_structure": wp["argument_structure"],
                    "common_patterns": wp["common_patterns"],
                    "analyzed_count": wp["analyzed_count"],
                }

            return jsonify(analytics_data)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/insights/recommendation")
    @login_required
    def api_recommendation():
        uid = current_user_id()
        profile = StudentProfileDB.load(uid)
        if not profile:
            return jsonify({"error": "No profile found"}), 404
        grade_log = GradeDetailLogDB(uid)
        rec = generate_recommendation(profile, grade_log)
        return jsonify(rec)

    @app.route("/api/analytics/weakness", methods=["POST"])
    @login_required
    def api_weakness_report():
        try:
            grader = get_grader()
            report = grader.get_weakness_report()
            return jsonify({"report": report})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/boundaries/<subject>/<level>")
    @login_required
    def api_boundaries(subject, level):
        try:
            engine = get_engine()
            result = engine.fetch_latest_boundaries(subject, level)
            return jsonify({
                "subject": result.subject,
                "level": result.level,
                "session": result.session,
                "boundaries": {str(k): v for k, v in result.boundaries.items()},
                "raw_text": result.raw_text,
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ── Subject Config & Topic APIs ────────────────────────────────

    @app.route("/api/subject-config/<subject>")
    @login_required
    def api_subject_config(subject):
        config = get_subject_config(subject)
        if not config:
            return jsonify({"error": "No config for this subject"}), 404

        assessment = config.assessment_hl  # Default to HL
        level = request.args.get("level", "HL")
        if level == "SL":
            assessment = config.assessment_sl

        return jsonify({
            "assessment": [
                {
                    "name": c.name,
                    "description": c.description,
                    "duration_minutes": c.duration_minutes,
                    "weighting_pct": c.weighting_pct,
                    "marks": c.marks,
                    "hl_only": c.hl_only,
                }
                for c in assessment
            ],
            "ia_description": config.ia_description,
            "ia_word_limit": config.ia_word_limit,
            "ia_weighting_pct": config.ia_weighting_pct,
            "key_command_terms": config.key_command_terms,
            "study_strategies": config.study_strategies,
            "common_pitfalls": config.common_pitfalls,
            "category": config.category,
        })

    @app.route("/api/topics/<subject>")
    @login_required
    def api_topics(subject):
        topics = get_syllabus_topics(subject)
        level = request.args.get("level", "HL")

        result = []
        for t in topics:
            if t.hl_only and level == "SL":
                continue
            result.append({
                "id": t.id,
                "name": t.name,
                "subtopics": t.subtopics,
                "hl_only": t.hl_only,
            })
        return jsonify({"topics": result})

    # ── Lifecycle routes ──────────────────────────────────────────

    @app.route("/lifecycle")
    @login_required
    def lifecycle_page():
        uid = current_user_id()
        profile = StudentProfileDB.load(uid)
        if not profile:
            return redirect(url_for("onboarding"))

        lifecycle = IBLifecycleDB(uid)
        return render_template(
            "lifecycle.html",
            profile=profile,
            lifecycle=lifecycle,
            summary=lifecycle.summary(),
            cas_outcomes=CAS_LEARNING_OUTCOMES,
        )

    @app.route("/lifecycle/ee")
    @login_required
    def lifecycle_ee():
        uid = current_user_id()
        profile = StudentProfileDB.load(uid)
        if not profile:
            return redirect(url_for("onboarding"))
        lifecycle = IBLifecycleDB(uid)
        return render_template("lifecycle.html", profile=profile, lifecycle=lifecycle,
                               summary=lifecycle.summary(), cas_outcomes=CAS_LEARNING_OUTCOMES,
                               section="ee")

    @app.route("/lifecycle/ia/<subject>")
    @login_required
    def lifecycle_ia(subject):
        uid = current_user_id()
        profile = StudentProfileDB.load(uid)
        if not profile:
            return redirect(url_for("onboarding"))
        lifecycle = IBLifecycleDB(uid)
        ia = lifecycle.get_ia_for_subject(subject)
        config = get_subject_config(subject)
        return render_template("lifecycle.html", profile=profile, lifecycle=lifecycle,
                               summary=lifecycle.summary(), cas_outcomes=CAS_LEARNING_OUTCOMES,
                               section="ia", ia_subject=subject, ia=ia,
                               ia_config=config)

    @app.route("/lifecycle/tok")
    @login_required
    def lifecycle_tok():
        uid = current_user_id()
        profile = StudentProfileDB.load(uid)
        if not profile:
            return redirect(url_for("onboarding"))
        lifecycle = IBLifecycleDB(uid)
        return render_template("lifecycle.html", profile=profile, lifecycle=lifecycle,
                               summary=lifecycle.summary(), cas_outcomes=CAS_LEARNING_OUTCOMES,
                               section="tok")

    @app.route("/lifecycle/cas")
    @login_required
    def lifecycle_cas():
        uid = current_user_id()
        profile = StudentProfileDB.load(uid)
        if not profile:
            return redirect(url_for("onboarding"))
        lifecycle = IBLifecycleDB(uid)
        return render_template("lifecycle.html", profile=profile, lifecycle=lifecycle,
                               summary=lifecycle.summary(), cas_outcomes=CAS_LEARNING_OUTCOMES,
                               section="cas")

    @app.route("/api/lifecycle/milestone", methods=["POST"])
    @login_required
    def api_lifecycle_milestone():
        data = request.get_json()
        milestone_id = data.get("milestone_id", "")
        if not milestone_id:
            return jsonify({"error": "milestone_id required"}), 400

        uid = current_user_id()
        lifecycle = IBLifecycleDB(uid)
        new_state = lifecycle.toggle_milestone(milestone_id)
        return jsonify({"completed": new_state, "summary": lifecycle.summary()})

    @app.route("/api/lifecycle/cas", methods=["POST"])
    @login_required
    def api_lifecycle_cas():
        data = request.get_json()
        reflection = CASReflection(
            strand=data.get("strand", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            date=data.get("date", date.today().isoformat()),
            learning_outcome=data.get("learning_outcome", ""),
            hours=float(data.get("hours", 0)),
        )

        if not reflection.strand or not reflection.title:
            return jsonify({"error": "Strand and title are required"}), 400

        uid = current_user_id()
        lifecycle = IBLifecycleDB(uid)
        lifecycle.add_cas_reflection(reflection)
        return jsonify({"success": True, "summary": lifecycle.summary()})

    @app.route("/api/lifecycle/update", methods=["POST"])
    @login_required
    def api_lifecycle_update():
        data = request.get_json()
        section = data.get("section", "")
        uid = current_user_id()
        lifecycle = IBLifecycleDB(uid)

        if section == "ee":
            lifecycle.update_ee(
                subject=data.get("subject", lifecycle.extended_essay.subject),
                research_question=data.get("research_question", lifecycle.extended_essay.research_question),
                supervisor=data.get("supervisor", lifecycle.extended_essay.supervisor),
                word_count=int(data.get("word_count", lifecycle.extended_essay.word_count)),
            )
        elif section == "tok":
            lifecycle.update_tok(
                essay_title=data.get("essay_title", lifecycle.tok.essay_title),
                prescribed_title_number=int(data.get("prescribed_title_number", lifecycle.tok.prescribed_title_number)),
                exhibition_theme=data.get("exhibition_theme", lifecycle.tok.exhibition_theme),
            )
        elif section == "ia":
            ia_subject = data.get("ia_subject", "")
            ia = lifecycle.get_ia_for_subject(ia_subject)
            if ia:
                lifecycle.update_ia(
                    ia_subject,
                    title=data.get("title", ia.title),
                    word_count=int(data.get("word_count", ia.word_count)),
                )
        else:
            return jsonify({"error": "Invalid section"}), 400

        return jsonify({"success": True, "summary": lifecycle.summary()})

    # ── Parent Portal routes ──────────────────────────────────────

    @app.route("/settings/parent")
    @login_required
    def parent_settings():
        uid = current_user_id()
        profile = StudentProfileDB.load(uid)
        if not profile:
            return redirect(url_for("onboarding"))
        parent_config = ParentConfigDB(uid)
        return render_template("parent_settings.html", profile=profile, parent_config=parent_config)

    @app.route("/api/parent/toggle", methods=["POST"])
    @login_required
    def api_parent_toggle():
        data = request.get_json()
        action = data.get("action", "")  # "enable"|"disable"|"regenerate"
        uid = current_user_id()
        parent_config = ParentConfigDB(uid)

        if action == "enable":
            parent_config.save_all(enabled=True)
            if not parent_config.token:
                parent_config.generate_token()
            profile = StudentProfileDB.load(uid)
            if profile and not parent_config.student_display_name:
                parent_config.save_all(student_display_name=profile.name)
        elif action == "disable":
            parent_config.save_all(enabled=False)
        elif action == "regenerate":
            parent_config.generate_token()

        return jsonify({
            "enabled": parent_config.enabled,
            "token": parent_config.token if parent_config.enabled else "",
        })

    @app.route("/api/parent/privacy", methods=["POST"])
    @login_required
    def api_parent_privacy():
        data = request.get_json()
        uid = current_user_id()
        parent_config = ParentConfigDB(uid)
        parent_config.save_all(
            student_display_name=data.get("student_display_name", parent_config.student_display_name),
            show_subject_grades=data.get("show_subject_grades", parent_config.show_subject_grades),
            show_recent_activity=data.get("show_recent_activity", parent_config.show_recent_activity),
            show_study_consistency=data.get("show_study_consistency", parent_config.show_study_consistency),
            show_command_term_stats=data.get("show_command_term_stats", parent_config.show_command_term_stats),
            show_insights=data.get("show_insights", parent_config.show_insights),
            show_exam_countdown=data.get("show_exam_countdown", parent_config.show_exam_countdown),
        )
        return jsonify({"success": True})

    @app.route("/parent/<token>")
    def parent_dashboard(token):
        parent_config = ParentConfigDB.load_by_token(token)
        if not parent_config:
            return render_template("parent_404.html"), 404

        user_id = parent_config.user_id
        profile = StudentProfileDB.load(user_id)
        if not profile:
            return render_template("parent_404.html"), 404

        grade_log = GradeDetailLogDB(user_id)
        activity_log = ActivityLogDB(user_id)

        # Build parent-safe data based on privacy toggles
        context = {
            "student_name": parent_config.student_display_name or profile.name,
            "config": parent_config,
        }

        if parent_config.show_exam_countdown:
            context["countdown"] = profile.exam_countdown()

        if parent_config.show_subject_grades:
            gaps = profile.compute_gaps(grade_log)
            context["gaps"] = gaps
            context["predicted_total"] = profile.compute_predicted_total(grade_log)
            context["target_total"] = profile.target_total_points

        if parent_config.show_recent_activity:
            context["recent_activity"] = activity_log.recent_activity(10)

        if parent_config.show_study_consistency:
            context["streak"] = activity_log.streak()
            context["days_active_30"] = activity_log.days_active_last_n(30)
            context["heatmap"] = activity_log.daily_heatmap(90)
            context["weekly_summary"] = activity_log.weekly_summary(4)

        if parent_config.show_insights:
            ct_stats = grade_log.command_term_stats()
            gaps = profile.compute_gaps(grade_log)
            context["insights"] = _generate_text_insights(grade_log, profile, ct_stats, gaps)

        # Generate alerts
        alerts = []
        if parent_config.show_study_consistency:
            days_inactive = (date.today() - _last_active_date(activity_log)).days
            if days_inactive >= 7:
                alerts.append({
                    "type": "warning",
                    "message": f"No study activity in the last {days_inactive} days.",
                })
        if parent_config.show_subject_grades:
            gaps = profile.compute_gaps(grade_log)
            for g in gaps:
                if g["status"] == "behind" and g["gap"] >= 2:
                    alerts.append({
                        "type": "concern",
                        "message": f"{g['subject']}: predicted {g['predicted']}, target {g['target']} ({g['gap']:+d} gap).",
                    })
        context["alerts"] = alerts

        return render_template("parent_dashboard.html", **context)

    # ── Study Planner routes ──────────────────────────────────────

    @app.route("/planner")
    @login_required
    def planner_page():
        uid = current_user_id()
        profile = StudentProfileDB.load(uid)
        if not profile:
            return redirect(url_for("onboarding"))

        plan_data = StudyPlanDB(uid).load()
        return render_template("planner.html", profile=profile, plan=plan_data, today=date.today().isoformat())

    @app.route("/api/planner/generate", methods=["POST"])
    @login_required
    def api_planner_generate():
        uid = current_user_id()
        profile = StudentProfileDB.load(uid)
        if not profile:
            return jsonify({"error": "No profile found"}), 404

        grade_log = GradeDetailLogDB(uid)
        review_sched = ReviewScheduleDB(uid)
        tp_store = TopicProgressStoreDB(uid)
        countdown = profile.exam_countdown()

        # Deterministic 14-day plan
        gaps = profile.compute_gaps(grade_log)
        due_items = review_sched.due_this_week()

        generated_date = date.today().isoformat()
        exam_date = countdown["exam_date"]
        daily_plans: list[DailyPlan] = []

        # Allocate subjects by gap size
        subject_weights: dict[str, float] = {}
        for g in gaps:
            if g["status"] == "behind":
                subject_weights[g["subject"]] = 3.0
            elif g["status"] == "close":
                subject_weights[g["subject"]] = 2.0
            elif g["status"] == "no_data":
                subject_weights[g["subject"]] = 1.5
            else:
                subject_weights[g["subject"]] = 1.0

        total_weight = sum(subject_weights.values())
        if total_weight == 0:
            total_weight = 1

        subjects_list = list(subject_weights.keys())
        daily_study_minutes = 120  # 2 hours per day

        for day_offset in range(14):
            d = date.today() + timedelta(days=day_offset)
            tasks: list[StudyTask] = []

            # Add due spaced repetition items for this day
            for item in due_items:
                review_date = date.fromisoformat(item.next_review)
                if review_date <= d and review_date > d - timedelta(days=2):
                    tasks.append(StudyTask(
                        subject=item.subject,
                        topic=item.topic,
                        task_type="review",
                        duration_minutes=15,
                        priority="high",
                    ))
                    if len(tasks) >= 2:
                        break

            # Distribute remaining time across subjects
            remaining_minutes = daily_study_minutes - sum(t.duration_minutes for t in tasks)

            # Rotate subjects across days
            day_subject_idx = day_offset % max(len(subjects_list), 1)
            primary_subject = subjects_list[day_subject_idx] if subjects_list else ""
            secondary_idx = (day_offset + 1) % max(len(subjects_list), 1)
            secondary_subject = subjects_list[secondary_idx] if subjects_list else ""

            if primary_subject and remaining_minutes > 0:
                # Check for uncovered syllabus topics
                topics = get_syllabus_topics(primary_subject)
                topic_name = "General practice"
                task_type = "practice"
                if topics:
                    tp = tp_store.get(primary_subject)
                    for t in topics:
                        if not tp.topics.get(t.id):
                            topic_name = t.name
                            break

                primary_minutes = min(remaining_minutes, 60)
                weight = subject_weights.get(primary_subject, 1)
                priority = "high" if weight >= 3 else "medium" if weight >= 2 else "low"

                tasks.append(StudyTask(
                    subject=primary_subject,
                    topic=topic_name,
                    task_type=task_type,
                    duration_minutes=primary_minutes,
                    priority=priority,
                ))
                remaining_minutes -= primary_minutes

            if secondary_subject and secondary_subject != primary_subject and remaining_minutes > 0:
                topics = get_syllabus_topics(secondary_subject)
                topic_name = "General practice"
                if topics:
                    tp = tp_store.get(secondary_subject)
                    for t in topics:
                        if not tp.topics.get(t.id):
                            topic_name = t.name
                            break

                tasks.append(StudyTask(
                    subject=secondary_subject,
                    topic=topic_name,
                    task_type="practice",
                    duration_minutes=min(remaining_minutes, 45),
                    priority="medium",
                ))

            # Add EE/IA work every few days
            if day_offset % 3 == 0:
                tasks.append(StudyTask(
                    subject="Extended Essay",
                    topic="EE work session",
                    task_type="ee_work",
                    duration_minutes=30,
                    priority="medium",
                ))

            total_mins = sum(t.duration_minutes for t in tasks)
            daily_plans.append(DailyPlan(
                date=d.isoformat(),
                tasks=tasks,
                estimated_minutes=total_mins,
            ))

        StudyPlanDB(uid).save(generated_date, exam_date, daily_plans)

        return jsonify({
            "success": True,
            "plan": {
                "generated_date": generated_date,
                "exam_date": exam_date,
                "daily_plans": [
                    {
                        "date": dp.date,
                        "estimated_minutes": dp.estimated_minutes,
                        "tasks": [
                            {
                                "subject": t.subject,
                                "topic": t.topic,
                                "task_type": t.task_type,
                                "duration_minutes": t.duration_minutes,
                                "priority": t.priority,
                                "completed": t.completed,
                            }
                            for t in dp.tasks
                        ],
                    }
                    for dp in daily_plans
                ],
            },
        })

    @app.route("/api/planner/complete", methods=["POST"])
    @login_required
    def api_planner_complete():
        data = request.get_json()
        day_date = data.get("date", "")
        task_index = int(data.get("task_index", -1))

        uid = current_user_id()
        plan_db = StudyPlanDB(uid)
        result = plan_db.update_task(day_date, task_index)

        if result is None:
            return jsonify({"error": "Task not found or no plan generated yet"}), 404

        # Award XP when completing a task (not when uncompleting)
        if result:
            gam = GamificationProfileDB(uid)
            gam.award_xp(XP_AWARDS["complete_planner_task"], "complete_planner_task")

        return jsonify({"completed": result})

    # ── Gamification API ──────────────────────────────────────────

    @app.route("/api/gamification")
    @login_required
    def api_gamification():
        uid = current_user_id()
        gam = GamificationProfileDB(uid)
        activity_log = ActivityLogDB(uid)
        gam.update_streak(activity_log)
        return jsonify({
            "total_xp": gam.total_xp,
            "level": gam.level,
            "xp_progress_pct": gam.xp_progress_pct,
            "xp_for_next_level": gam.xp_for_next_level,
            "current_streak": gam.current_streak,
            "longest_streak": gam.longest_streak,
            "daily_xp_today": gam.daily_xp_today,
            "daily_goal_xp": gam.daily_goal_xp,
            "daily_goal_pct": gam.daily_goal_pct,
            "badges": [
                {**BADGE_DEFINITIONS.get(b, {"name": b}), "id": b}
                for b in gam.badges
            ],
            "streak_freeze_available": gam.streak_freeze_available,
            "total_questions_answered": gam.total_questions_answered,
        })

    # ── Flashcard routes ──────────────────────────────────────────

    @app.route("/flashcards")
    @login_required
    def flashcards_page():
        uid = current_user_id()
        profile = StudentProfileDB.load(uid)
        if not profile:
            return redirect(url_for("onboarding"))
        fc_deck = FlashcardDeckDB(uid)
        return render_template("flashcards.html", profile=profile,
                               due_count=fc_deck.due_count(),
                               total_cards=len(fc_deck.cards))

    @app.route("/api/flashcards")
    @login_required
    def api_flashcards():
        uid = current_user_id()
        fc_deck = FlashcardDeckDB(uid)
        subject = request.args.get("subject", "")
        mode = request.args.get("mode", "due")  # "due" | "all" | "subject"

        if mode == "due":
            cards = fc_deck.due_today()
        elif mode == "subject" and subject:
            cards = fc_deck.by_subject(subject)
        else:
            cards = fc_deck.cards

        return jsonify({
            "cards": [
                {
                    "id": c.id,
                    "front": c.front,
                    "back": c.back,
                    "subject": c.subject,
                    "topic": c.topic,
                    "source": c.source,
                    "interval_days": c.interval_days,
                    "next_review": c.next_review,
                    "review_count": c.review_count,
                }
                for c in cards
            ],
            "due_count": fc_deck.due_count(),
            "total": len(fc_deck.cards),
        })

    @app.route("/api/flashcards/review", methods=["POST"])
    @login_required
    def api_flashcard_review():
        data = request.get_json()
        card_id = data.get("card_id", "")
        rating = int(data.get("rating", 3))  # 1=Again, 2=Hard, 3=Good, 4=Easy

        if not card_id or rating not in (1, 2, 3, 4):
            return jsonify({"error": "card_id and rating (1-4) required"}), 400

        uid = current_user_id()
        fc_deck = FlashcardDeckDB(uid)
        fc_deck.review(card_id, rating)

        # Award XP
        gam = GamificationProfileDB(uid)
        gam.award_xp(XP_AWARDS["review_flashcard"], "review_flashcard")
        gam.total_flashcards_reviewed += 1
        gam.check_badges()
        gam.save()

        return jsonify({
            "success": True,
            "xp_earned": XP_AWARDS["review_flashcard"],
            "due_remaining": fc_deck.due_count(),
        })

    @app.route("/api/flashcards/create", methods=["POST"])
    @login_required
    def api_flashcard_create():
        data = request.get_json()
        front = data.get("front", "").strip()
        back = data.get("back", "").strip()
        subject = data.get("subject", "").strip()
        topic = data.get("topic", "")

        if not front or not back or not subject:
            return jsonify({"error": "front, back, and subject are required"}), 400

        uid = current_user_id()
        fc_deck = FlashcardDeckDB(uid)
        card = Flashcard(
            id="",
            front=front,
            back=back,
            subject=subject,
            topic=topic,
            source="manual",
        )
        fc_deck.add(card)
        return jsonify({"success": True, "card_id": card.id})

    @app.route("/api/flashcards/<card_id>", methods=["DELETE"])
    @login_required
    def api_flashcard_delete(card_id):
        uid = current_user_id()
        fc_deck = FlashcardDeckDB(uid)
        if fc_deck.delete(card_id):
            return jsonify({"success": True})
        return jsonify({"error": "Card not found"}), 404

    # ── Hint (Socratic questioning) ──────────────────────────────

    @app.route("/api/study/hint", methods=["POST"])
    @login_required
    def api_study_hint():
        data = request.get_json()
        question = data.get("question", "")
        command_term = data.get("command_term", "")
        hint_level = int(data.get("hint_level", 1))  # 1-3 progressive hints

        if not question:
            return jsonify({"error": "question is required"}), 400

        try:
            engine = get_engine()

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

    # ── Misconception API ────────────────────────────────────────

    @app.route("/api/misconceptions")
    @login_required
    def api_misconceptions():
        uid = current_user_id()
        misc_log = MisconceptionLogDB(uid)
        subject = request.args.get("subject", "")
        return jsonify({
            "misconceptions": misc_log.active_misconceptions(subject),
        })

    # ── Mock Exam Report API ─────────────────────────────────────

    @app.route("/api/mock-reports")
    @login_required
    def api_mock_reports():
        uid = current_user_id()
        store = MockExamReportStoreDB(uid)
        subject = request.args.get("subject", "")
        if subject:
            reports = store.by_subject(subject)
        else:
            reports = store.recent(10)
        return jsonify({
            "reports": [
                {
                    "id": r.id,
                    "subject": r.subject,
                    "level": r.level,
                    "date": r.date,
                    "percentage": r.percentage,
                    "grade": r.grade,
                    "total_marks_earned": r.total_marks_earned,
                    "total_marks_possible": r.total_marks_possible,
                    "command_term_breakdown": r.command_term_breakdown,
                    "improvements": r.improvements,
                    "created_at": r.created_at,
                }
                for r in reports
            ],
        })

    # ── Mock Exam Report Creation ────────────────────────────────

    @app.route("/api/mock-reports/create", methods=["POST"])
    @login_required
    def api_mock_report_create():
        """Create a mock exam report from completed exam sim session results."""
        data = request.get_json()
        subject = data.get("subject", "")
        level = data.get("level", "HL")
        results = data.get("results", [])  # [{question, marks, mark_earned, percentage, command_term, improvements}]

        if not subject or not results:
            return jsonify({"error": "Subject and results are required"}), 400

        total_earned = sum(r.get("mark_earned", 0) for r in results)
        total_possible = sum(r.get("marks", 0) for r in results)
        overall_pct = round(total_earned / total_possible * 100) if total_possible > 0 else 0

        # Determine grade from percentage
        config = get_subject_config(subject)
        boundaries = {}
        if config:
            boundaries = config.grade_boundaries_hl if level == "HL" else config.grade_boundaries_sl
        grade = 1
        for g in sorted(boundaries.keys(), reverse=True):
            if overall_pct >= boundaries[g]:
                grade = g
                break

        # Command term breakdown
        ct_breakdown = {}
        for r in results:
            ct = r.get("command_term", "Unknown")
            if ct not in ct_breakdown:
                ct_breakdown[ct] = {"total": 0, "earned": 0, "count": 0}
            ct_breakdown[ct]["total"] += r.get("marks", 0)
            ct_breakdown[ct]["earned"] += r.get("mark_earned", 0)
            ct_breakdown[ct]["count"] += 1

        # Collect improvements
        all_improvements = []
        for r in results:
            all_improvements.extend(r.get("improvements", []))

        # Generate AI summary of improvements
        improvements_text = []
        if all_improvements:
            # Deduplicate and take top 3
            seen = set()
            for imp in all_improvements:
                key = imp.lower().strip()[:50]
                if key not in seen:
                    seen.add(key)
                    improvements_text.append(imp)
                if len(improvements_text) >= 5:
                    break

        report = MockExamReport(
            id=datetime.now().strftime("%Y%m%d_%H%M%S"),
            subject=subject,
            level=level,
            date=datetime.now().strftime("%Y-%m-%d"),
            percentage=overall_pct,
            grade=grade,
            total_marks_earned=total_earned,
            total_marks_possible=total_possible,
            command_term_breakdown=ct_breakdown,
            improvements=improvements_text[:5],
            created_at=datetime.now().isoformat(),
        )

        uid = current_user_id()
        store = MockExamReportStoreDB(uid)
        store.add(report)

        # Award badge for mock exam completion
        gam = GamificationProfileDB(uid)
        gam.check_badges(questions_answered=0, subjects=set(), mock_complete=True)
        gam.save()

        return jsonify({
            "success": True,
            "report": {
                "id": report.id,
                "grade": report.grade,
                "percentage": report.percentage,
                "total_marks_earned": report.total_marks_earned,
                "total_marks_possible": report.total_marks_possible,
                "command_term_breakdown": report.command_term_breakdown,
                "improvements": report.improvements,
            }
        })

    # ── EE/IA Draft Feedback ─────────────────────────────────────

    @app.route("/api/lifecycle/draft-feedback", methods=["POST"])
    @login_required
    def api_draft_feedback():
        data = request.get_json()
        draft_text = data.get("text", "").strip()
        section = data.get("section", "")  # "ee" | "ia"
        subject = data.get("subject", "")

        if not draft_text or not section:
            return jsonify({"error": "text and section are required"}), 400

        try:
            engine = get_engine()

            if section == "ee":
                rubric = """EE Assessment Criteria:
A. Focus & Method (6 marks): Clear research question, appropriate methodology
B. Knowledge & Understanding (6 marks): Relevant subject knowledge, context
C. Critical Thinking (12 marks): Analysis, evaluation, discussion, argumentation
D. Presentation (4 marks): Structure, layout, referencing
E. Engagement (6 marks): Personal intellectual initiative, process"""
            else:
                config = get_subject_config(subject)
                ia_desc = config.ia_description if config else "Subject-specific internal assessment"
                ia_word_limit = config.ia_word_limit if config else "Unknown"
                rubric = f"""IA for {subject}:
Description: {ia_desc}
Word limit: {ia_word_limit}
Assess against: Personal engagement, Exploration, Analysis, Evaluation, Communication"""

            prompt = f"""You are an experienced IB examiner. Provide rubric-aligned feedback on this student draft.

{rubric}

STUDENT DRAFT (excerpt):
{draft_text[:6000]}

WORD COUNT: {len(draft_text.split())} words

Provide:
1. OVERALL IMPRESSION (1-2 sentences)
2. RUBRIC FEEDBACK: For each criterion, give a brief assessment (Developing/Adequate/Good/Excellent) and 1 specific improvement
3. TOP 3 PRIORITIES to improve this draft
4. STRENGTHS (2-3 things done well)

Be constructive and specific. Reference actual text where possible."""

            feedback = engine.ask(prompt)
            return jsonify({
                "feedback": feedback,
                "word_count": len(draft_text.split()),
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ── Research Question Quality Check ──────────────────────────

    @app.route("/api/lifecycle/rq-check", methods=["POST"])
    @login_required
    def api_rq_check():
        data = request.get_json()
        rq = data.get("research_question", "").strip()
        subject = data.get("subject", "")

        if not rq:
            return jsonify({"error": "research_question is required"}), 400

        try:
            engine = get_engine()
            prompt = f"""You are an IB Extended Essay supervisor. Evaluate this research question for a {subject} EE:

Research Question: "{rq}"

Assess against IB criteria:
1. FOCUSED: Is it narrow enough to be answered in 4000 words?
2. RESEARCHABLE: Can it be investigated with available methods/sources?
3. SUBJECT-APPROPRIATE: Does it fit within {subject} methodology?
4. ANALYTICAL: Does it invite analysis rather than description?

Rate each criterion: Strong / Adequate / Needs Work
Give 1-2 sentences of specific feedback per criterion.
End with an OVERALL rating (Strong / Adequate / Needs Work) and a SUGGESTED IMPROVEMENT if applicable."""

            feedback = engine.ask(prompt)
            return jsonify({"feedback": feedback})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ── Adaptive Difficulty API ──────────────────────────────────

    @app.route("/api/difficulty/<subject>")
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

    # ── Service Worker route (must be served from root) ──────────

    @app.route("/sw.js")
    def service_worker():
        from flask import send_from_directory
        return send_from_directory(
            current_app.static_folder, "sw.js",
            mimetype="application/javascript",
            max_age=0,
        )

    # ── Export & Reporting routes ────────────────────────────────

    @app.route("/api/export/report")
    @login_required
    def api_export_report():
        """Generate and return a PDF progress report."""
        uid = current_user_id()
        profile = StudentProfileDB.load(uid)
        if not profile:
            return jsonify({"error": "No profile found"}), 404

        from export import generate_pdf_report
        from flask import Response

        grade_log = GradeDetailLogDB(uid)
        activity_log = ActivityLogDB(uid)
        gam = GamificationProfileDB(uid)
        tp_store = TopicProgressStoreDB(uid)
        misc_log = MisconceptionLogDB(uid)

        pdf_bytes = generate_pdf_report(
            profile=profile,
            grade_log=grade_log,
            activity_log=activity_log,
            gamification=gam,
            topic_progress=tp_store,
            misconception_log=misc_log,
        )

        safe_name = profile.name.replace(" ", "_")
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="IB_Progress_Report_{safe_name}_{date.today().isoformat()}.pdf"'
            },
        )

    @app.route("/api/export/grades")
    @login_required
    def api_export_grades():
        """Export grade history as CSV."""
        import csv
        import io
        from flask import Response

        uid = current_user_id()
        grade_log = GradeDetailLogDB(uid)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Date", "Subject", "Level", "Command Term", "Topic",
            "Mark Earned", "Mark Total", "Percentage", "Grade",
            "Strengths", "Improvements", "Examiner Tip",
        ])

        for e in grade_log.entries:
            writer.writerow([
                e.timestamp[:10] if e.timestamp else "",
                e.subject_display, e.level, e.command_term, e.topic,
                e.mark_earned, e.mark_total, e.percentage, e.grade,
                "; ".join(e.strengths), "; ".join(e.improvements), e.examiner_tip,
            ])

        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="IB_Grades_{date.today().isoformat()}.csv"'
            },
        )

    # ── Notification routes ──────────────────────────────────────

    @app.route("/api/notifications")
    @login_required
    def api_notifications():
        """Return recent notifications and generate any pending ones."""
        uid = current_user_id()
        generate_pending_notifications(uid)
        store = NotificationStoreDB(uid)
        from dataclasses import asdict
        return jsonify({
            "notifications": [asdict(n) for n in store.recent(20)],
            "unread_count": store.unread_count(),
        })

    @app.route("/api/notifications/read", methods=["POST"])
    @login_required
    def api_notifications_read():
        data = request.get_json()
        notif_id = data.get("id", "")
        uid = current_user_id()
        store = NotificationStoreDB(uid)
        if notif_id == "all":
            store.mark_all_read()
        else:
            store.mark_read(notif_id)
        return jsonify({"success": True})

    @app.route("/api/notifications/dismiss", methods=["POST"])
    @login_required
    def api_notifications_dismiss():
        data = request.get_json()
        uid = current_user_id()
        store = NotificationStoreDB(uid)
        store.dismiss(data.get("id", ""))
        return jsonify({"success": True})

    # ── Collaboration: Question Sharing routes ───────────────────

    @app.route("/api/questions/export", methods=["POST"])
    @login_required
    def api_questions_export():
        """Export a question set as shareable JSON."""
        data = request.get_json()
        title = data.get("title", "Shared Questions")
        description = data.get("description", "")
        questions = data.get("questions", [])
        subject = data.get("subject", "")
        topic = data.get("topic", "")
        level = data.get("level", "HL")

        if not questions:
            return jsonify({"error": "No questions to export"}), 400

        uid = current_user_id()
        profile = StudentProfileDB.load(uid)
        author = profile.name if profile else "Anonymous"

        store = SharedQuestionStoreDB(uid)
        qset = store.export_set(title, description, subject, topic, level, questions, author)

        return jsonify({
            "success": True,
            "json_data": json.loads(store.to_json(qset.id)),
        })

    @app.route("/api/questions/import", methods=["POST"])
    @login_required
    def api_questions_import():
        """Import a question set from JSON."""
        data = request.get_json()

        required = ["questions", "subject"]
        if not all(k in data for k in required):
            return jsonify({"error": "Invalid question set format"}), 400

        if not data.get("questions") or len(data["questions"]) == 0:
            return jsonify({"error": "No questions in set"}), 400

        uid = current_user_id()
        store = SharedQuestionStoreDB(uid)
        qset = store.import_set({
            "id": data.get("id", f"imported_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
            "title": data.get("title", "Imported Questions"),
            "description": data.get("description", ""),
            "author": data.get("author", "Unknown"),
            "subject": data["subject"],
            "topic": data.get("topic", ""),
            "level": data.get("level", "HL"),
            "questions": data["questions"],
            "created_at": data.get("created_at", datetime.now().isoformat()),
        })

        return jsonify({
            "success": True,
            "set_id": qset.id,
            "question_count": len(qset.questions),
        })

    @app.route("/api/questions/shared")
    @login_required
    def api_shared_questions():
        """List all shared/imported question sets."""
        uid = current_user_id()
        store = SharedQuestionStoreDB(uid)
        from dataclasses import asdict
        return jsonify({
            "sets": [asdict(qs) for qs in store.sets],
        })

    # ══════════════════════════════════════════════════════════════════
    # ─── STUDY GROUPS & SOCIAL (Step 4) ──────────────────────────────
    # ══════════════════════════════════════════════════════════════════

    @app.route("/groups")
    @login_required
    def groups_page():
        uid = current_user_id()
        profile = StudentProfileDB(uid)
        gam = GamificationProfileDB(uid)
        return render_template("groups.html", profile=profile, gam=gam)

    @app.route("/api/groups", methods=["POST"])
    @login_required
    def api_create_group():
        uid = current_user_id()
        data = request.get_json(force=True)
        result = StudyGroupStoreDB.create(
            name=data.get("name", "Study Group"),
            created_by=uid,
            subject=data.get("subject", ""),
            level=data.get("level", ""),
            max_members=data.get("max_members", 20),
        )
        return jsonify({"success": True, **result})

    @app.route("/api/groups")
    @login_required
    def api_list_groups():
        uid = current_user_id()
        return jsonify({"groups": StudyGroupStoreDB.user_groups(uid)})

    @app.route("/api/groups/<int:group_id>")
    @login_required
    def api_get_group(group_id):
        group = StudyGroupStoreDB.get(group_id)
        if not group:
            return jsonify({"error": "Group not found"}), 404
        members = StudyGroupStoreDB.members(group_id)
        challenges = ChallengeStoreDB.group_challenges(group_id)
        return jsonify({"group": group, "members": members, "challenges": challenges})

    @app.route("/api/groups/<int:group_id>/join", methods=["POST"])
    @login_required
    def api_join_group(group_id):
        uid = current_user_id()
        data = request.get_json(force=True)
        invite_code = data.get("invite_code", "")
        group = StudyGroupStoreDB.get(group_id)
        if not group or group["invite_code"] != invite_code:
            return jsonify({"error": "Invalid invite code"}), 400
        ok = StudyGroupStoreDB.join(group_id, uid)
        return jsonify({"success": ok})

    @app.route("/api/groups/join", methods=["POST"])
    @login_required
    def api_join_group_by_code():
        uid = current_user_id()
        data = request.get_json(force=True)
        code = data.get("invite_code", "")
        group = StudyGroupStoreDB.get_by_invite(code)
        if not group:
            return jsonify({"error": "Invalid invite code"}), 404
        ok = StudyGroupStoreDB.join(group["id"], uid)
        return jsonify({"success": ok, "group_id": group["id"]})

    @app.route("/api/groups/<int:group_id>/leave", methods=["POST"])
    @login_required
    def api_leave_group(group_id):
        uid = current_user_id()
        StudyGroupStoreDB.leave(group_id, uid)
        return jsonify({"success": True})

    @app.route("/api/challenges", methods=["POST"])
    @login_required
    def api_create_challenge():
        uid = current_user_id()
        data = request.get_json(force=True)
        challenge_id = ChallengeStoreDB.create(
            group_id=data["group_id"],
            challenger_id=uid,
            title=data.get("title", "Challenge"),
            subject=data.get("subject", ""),
            config=data.get("config"),
        )
        return jsonify({"success": True, "challenge_id": challenge_id})

    @app.route("/api/challenges/<int:challenge_id>")
    @login_required
    def api_get_challenge(challenge_id):
        challenge = ChallengeStoreDB.get(challenge_id)
        if not challenge:
            return jsonify({"error": "Not found"}), 404
        lb = ChallengeStoreDB.leaderboard(challenge_id)
        return jsonify({"challenge": challenge, "leaderboard": lb})

    @app.route("/api/challenges/<int:challenge_id>/submit", methods=["POST"])
    @login_required
    def api_submit_challenge(challenge_id):
        uid = current_user_id()
        data = request.get_json(force=True)
        ok = ChallengeStoreDB.submit_score(challenge_id, uid, data.get("score", 0))
        return jsonify({"success": ok})

    @app.route("/api/leaderboard")
    @login_required
    def api_leaderboard():
        scope = request.args.get("scope", "global")
        scope_id = int(request.args.get("scope_id", 0))
        period = request.args.get("period", "all")
        entries = LeaderboardStoreDB.get(scope, scope_id, period)
        return jsonify({"leaderboard": entries})

    # ══════════════════════════════════════════════════════════════════
    # ─── TRY-BEFORE-SIGNUP / GUEST MODE (Step 5) ────────────────────
    # ══════════════════════════════════════════════════════════════════

    from flask import session as flask_session

    @app.route("/try")
    def try_page():
        flask_session["guest"] = True
        flask_session["guest_questions"] = 0
        return render_template("try.html", show_sidebar=False)

    @app.before_request
    def _guest_middleware():
        """Limit guest users to 3 questions and block non-study routes."""
        if flask_session.get("guest") and not current_user.is_authenticated:
            allowed = ["/try", "/static", "/login", "/register", "/api/study/generate",
                       "/api/study/grade", "/study", "/sw.js", "/analytics",
                       "/api/analytics", "/api/push/vapid-key", "/community-analytics"]

            # Enforce 3-question limit on study API calls
            if request.path in ("/api/study/generate", "/api/study/grade"):
                used = flask_session.get("guest_questions", 0)
                if used >= 3:
                    return jsonify({
                        "error": "You've used all 3 free questions. Sign up to continue!",
                        "guest_limit": True,
                        "used": used,
                        "limit": 3,
                    }), 403

            if not any(request.path.startswith(p) for p in allowed):
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Sign up for full access", "guest_limit": True}), 403
                return redirect(url_for("try_page"))

    # ══════════════════════════════════════════════════════════════════
    # ─── PUSH NOTIFICATIONS (Step 6) ─────────────────────────────────
    # ══════════════════════════════════════════════════════════════════

    @app.route("/api/push/subscribe", methods=["POST"])
    @login_required
    def api_push_subscribe():
        uid = current_user_id()
        data = request.get_json(force=True)
        sub = data.get("subscription", {})
        PushSubscriptionStoreDB.subscribe(
            user_id=uid,
            endpoint=sub.get("endpoint", ""),
            p256dh=sub.get("keys", {}).get("p256dh", ""),
            auth=sub.get("keys", {}).get("auth", ""),
        )
        return jsonify({"success": True})

    @app.route("/api/push/unsubscribe", methods=["POST"])
    @login_required
    def api_push_unsubscribe():
        data = request.get_json(force=True)
        PushSubscriptionStoreDB.unsubscribe(data.get("endpoint", ""))
        return jsonify({"success": True})

    @app.route("/api/push/vapid-key")
    def api_vapid_key():
        key = os.environ.get("VAPID_PUBLIC_KEY", "")
        return jsonify({"publicKey": key})

    # ══════════════════════════════════════════════════════════════════
    # ─── COMMUNITY PAPERS (Step 7) ───────────────────────────────────
    # ══════════════════════════════════════════════════════════════════

    @app.route("/community")
    @login_required
    def community_page():
        uid = current_user_id()
        profile = StudentProfileDB(uid)
        gam = GamificationProfileDB(uid)
        return render_template("community.html", profile=profile, gam=gam)

    @app.route("/api/papers")
    @login_required
    def api_list_papers():
        subject = request.args.get("subject", "")
        level = request.args.get("level", "")
        papers = CommunityPaperStoreDB.list_papers(subject=subject, level=level)
        return jsonify({"papers": papers})

    @app.route("/api/papers", methods=["POST"])
    @login_required
    def api_upload_paper():
        uid = current_user_id()
        data = request.get_json(force=True)
        paper_id = CommunityPaperStoreDB.create(
            uploader_id=uid,
            title=data.get("title", ""),
            subject=data.get("subject", ""),
            level=data.get("level", ""),
            year=data.get("year", 0),
            session=data.get("session", ""),
            paper_number=data.get("paper_number", 0),
            questions=data.get("questions"),
        )
        return jsonify({"success": True, "paper_id": paper_id})

    @app.route("/api/papers/<int:paper_id>")
    @login_required
    def api_get_paper(paper_id):
        paper = CommunityPaperStoreDB.get(paper_id)
        if not paper:
            return jsonify({"error": "Not found"}), 404
        CommunityPaperStoreDB.increment_downloads(paper_id)
        return jsonify({"paper": paper})

    @app.route("/api/papers/<int:paper_id>/rate", methods=["POST"])
    @login_required
    def api_rate_paper(paper_id):
        uid = current_user_id()
        data = request.get_json(force=True)
        CommunityPaperStoreDB.rate(paper_id, uid, data.get("rating", 5))
        return jsonify({"success": True})

    @app.route("/api/papers/<int:paper_id>/report", methods=["POST"])
    @login_required
    def api_report_paper(paper_id):
        uid = current_user_id()
        data = request.get_json(force=True)
        CommunityPaperStoreDB.report(paper_id, uid, data.get("reason", ""))
        return jsonify({"success": True})

    @app.route("/api/papers/<int:paper_id>/approve", methods=["POST"])
    @login_required
    def api_approve_paper(paper_id):
        if not (current_user.is_authenticated and getattr(current_user, "role", "") in ("teacher", "admin")):
            return jsonify({"error": "Forbidden"}), 403
        CommunityPaperStoreDB.approve(paper_id)
        return jsonify({"success": True})

    # ══════════════════════════════════════════════════════════════════
    # ─── TEACHER DASHBOARD (Step 8) ──────────────────────────────────
    # ══════════════════════════════════════════════════════════════════

    def teacher_required(f):
        """Decorator that requires user to have teacher or admin role."""
        from functools import wraps
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if getattr(current_user, "role", "student") not in ("teacher", "admin"):
                abort(403)
            return f(*args, **kwargs)
        return decorated

    @app.route("/teacher/dashboard")
    @teacher_required
    def teacher_dashboard():
        uid = current_user_id()
        profile = StudentProfileDB(uid)
        gam = GamificationProfileDB(uid)
        classes = ClassStoreDB.teacher_classes(uid)
        return render_template("teacher_dashboard.html", profile=profile, gam=gam, classes=classes)

    @app.route("/teacher/classes", methods=["POST"])
    @teacher_required
    def teacher_create_class():
        uid = current_user_id()
        data = request.get_json(force=True)
        result = ClassStoreDB.create(
            teacher_id=uid,
            name=data.get("name", ""),
            subject=data.get("subject", ""),
            level=data.get("level", ""),
            school_id=data.get("school_id"),
        )
        return jsonify({"success": True, **result})

    @app.route("/teacher/classes/<int:class_id>")
    @teacher_required
    def teacher_class_detail(class_id):
        uid = current_user_id()
        cls = ClassStoreDB.get(class_id)
        if not cls or cls["teacher_id"] != uid:
            abort(404)
        profile = StudentProfileDB(uid)
        gam = GamificationProfileDB(uid)
        members = ClassStoreDB.members(class_id)
        progress = ClassStoreDB.student_progress(class_id)
        avg_grades = ClassStoreDB.class_avg_grades(class_id)
        assignments = AssignmentStoreDB.list_for_class(class_id)
        return render_template("class_detail.html", profile=profile, gam=gam,
                               cls=cls, members=members, progress=progress,
                               avg_grades=avg_grades, assignments=assignments)

    @app.route("/teacher/assignments", methods=["POST"])
    @teacher_required
    def teacher_create_assignment():
        data = request.get_json(force=True)
        aid = AssignmentStoreDB.create(
            class_id=data["class_id"],
            title=data.get("title", ""),
            description=data.get("description", ""),
            due_date=data.get("due_date", ""),
            config=data.get("config"),
        )
        return jsonify({"success": True, "assignment_id": aid})

    @app.route("/teacher/assignments/<int:assignment_id>/submissions")
    @teacher_required
    def teacher_assignment_submissions(assignment_id):
        subs = AssignmentStoreDB.submissions(assignment_id)
        return jsonify({"submissions": subs})

    @app.route("/api/teacher/stats")
    @teacher_required
    def api_teacher_stats():
        uid = current_user_id()
        classes = ClassStoreDB.teacher_classes(uid)
        total_students = sum(c.get("member_count", 0) for c in classes)
        return jsonify({
            "class_count": len(classes),
            "total_students": total_students,
            "classes": classes,
        })

    @app.route("/api/teacher/class/<int:class_id>/topic-gaps")
    @teacher_required
    def api_teacher_topic_gaps(class_id):
        uid = current_user_id()
        cls = ClassStoreDB.get(class_id)
        if not cls or cls["teacher_id"] != uid:
            abort(404)
        gaps = ClassStoreDB.topic_gaps(class_id)
        return jsonify({"topic_gaps": gaps})

    @app.route("/api/teacher/class/<int:class_id>/at-risk")
    @teacher_required
    def api_teacher_at_risk(class_id):
        uid = current_user_id()
        cls = ClassStoreDB.get(class_id)
        if not cls or cls["teacher_id"] != uid:
            abort(404)
        students = ClassStoreDB.at_risk_students(class_id)
        return jsonify({"at_risk_students": students})

    @app.route("/api/teacher/class/<int:class_id>/export")
    @teacher_required
    def api_teacher_export_csv(class_id):
        uid = current_user_id()
        cls = ClassStoreDB.get(class_id)
        if not cls or cls["teacher_id"] != uid:
            abort(404)
        csv_data = ClassStoreDB.export_class_csv(class_id)
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename=class_{class_id}_report.csv"},
        )

    @app.route("/api/classes/join", methods=["POST"])
    @login_required
    def api_join_class():
        uid = current_user_id()
        data = request.get_json(force=True)
        code = data.get("join_code", "")
        cls = ClassStoreDB.get_by_join_code(code)
        if not cls:
            return jsonify({"error": "Invalid class code"}), 404
        ok = ClassStoreDB.join(cls["id"], uid)
        return jsonify({"success": ok, "class_id": cls["id"]})

    @app.route("/api/assignments")
    @login_required
    def api_student_assignments():
        uid = current_user_id()
        return jsonify({"assignments": AssignmentStoreDB.student_assignments(uid)})

    # ══════════════════════════════════════════════════════════════════
    # ─── ADAPTIVE DIFFICULTY (Step 9) ────────────────────────────────
    # ══════════════════════════════════════════════════════════════════

    @app.route("/api/ability/<subject>")
    @login_required
    def api_ability_profile(subject):
        uid = current_user_id()
        store = StudentAbilityStoreDB(uid)
        profile = store.get_profile(subject)
        return jsonify({"abilities": profile})

    # ══════════════════════════════════════════════════════════════════
    # ─── EXAM SIMULATION (Step 10) ───────────────────────────────────
    # ══════════════════════════════════════════════════════════════════

    @app.route("/api/exam/generate", methods=["POST"])
    @login_required
    def api_exam_generate():
        uid = current_user_id()
        data = request.get_json(force=True)
        subject = data.get("subject", "Biology")
        level = data.get("level", "HL")
        paper_number = data.get("paper_number", 1)

        try:
            from exam_simulation import ExamPaperGenerator
            gen = ExamPaperGenerator(get_engine())
            paper = gen.generate_paper(subject, level, paper_number)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

        store = ExamSessionStoreDB(uid)
        session_id = store.create(
            subject=subject, level=level, paper_number=paper_number,
            duration_minutes=paper.get("duration_minutes", 90),
            questions=paper.get("questions", []),
        )
        return jsonify({"success": True, "session_id": session_id, "paper": paper})

    @app.route("/api/exam/<int:session_id>/submit", methods=["POST"])
    @login_required
    def api_exam_submit(session_id):
        uid = current_user_id()
        data = request.get_json(force=True)
        store = ExamSessionStoreDB(uid)

        from exam_simulation import ExamPaperGenerator
        grade = ExamPaperGenerator.calculate_grade(
            data.get("subject", ""),
            data.get("level", "HL"),
            data.get("total_marks", 0),
            data.get("earned_marks", 0),
        )

        store.complete(
            session_id=session_id,
            answers=data.get("answers", []),
            earned_marks=data.get("earned_marks", 0),
            total_marks=data.get("total_marks", 0),
            grade=grade,
        )
        return jsonify({"success": True, "grade": grade})

    @app.route("/api/exam/<int:session_id>/results")
    @login_required
    def api_exam_results(session_id):
        uid = current_user_id()
        store = ExamSessionStoreDB(uid)
        session = store.get(session_id)
        if not session:
            return jsonify({"error": "Not found"}), 404
        return jsonify({"session": session})

    @app.route("/api/exam/history")
    @login_required
    def api_exam_history():
        uid = current_user_id()
        store = ExamSessionStoreDB(uid)
        return jsonify({"sessions": store.list_sessions()})

    # ══════════════════════════════════════════════════════════════════
    # ─── AI TUTOR (Step 11) ──────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════

    @app.route("/tutor")
    @login_required
    def tutor_page():
        uid = current_user_id()
        profile = StudentProfileDB(uid)
        gam = GamificationProfileDB(uid)
        return render_template("tutor.html", profile=profile, gam=gam)

    @app.route("/api/tutor/start", methods=["POST"])
    @login_required
    def api_tutor_start():
        uid = current_user_id()
        data = request.get_json(force=True)
        store = TutorConversationStoreDB(uid)
        conv_id = store.create(
            subject=data.get("subject", ""),
            topic=data.get("topic", ""),
        )
        return jsonify({"success": True, "conversation_id": conv_id})

    @app.route("/api/tutor/message", methods=["POST"])
    @login_required
    def api_tutor_message():
        uid = current_user_id()
        data = request.get_json(force=True)
        conv_id = data.get("conversation_id")
        user_message = data.get("message", "")

        store = TutorConversationStoreDB(uid)
        conv = store.get(conv_id)
        if not conv:
            return jsonify({"error": "Conversation not found"}), 404

        store.add_message(conv_id, "user", user_message)

        try:
            from tutor import TutorSession
            ability_store = StudentAbilityStoreDB(uid)
            ability = ability_store.get_theta(conv.get("subject", ""), conv.get("topic", ""))
            tutor = TutorSession(
                subject=conv.get("subject", ""),
                topic=conv.get("topic", ""),
                ability_theta=ability.get("theta", 0.0),
            )
            response = tutor.respond(conv["messages"] + [{"role": "user", "content": user_message}])
        except ImportError:
            response = "The AI tutor requires the Gemini API. Please configure your API key."
        except Exception as e:
            response = f"I encountered an issue: {str(e)}"

        store.add_message(conv_id, "assistant", response)
        return jsonify({"success": True, "response": response})

    @app.route("/api/tutor/history")
    @login_required
    def api_tutor_history():
        uid = current_user_id()
        store = TutorConversationStoreDB(uid)
        return jsonify({"conversations": store.list_conversations()})

    @app.route("/api/tutor/<int:conv_id>")
    @login_required
    def api_tutor_get(conv_id):
        uid = current_user_id()
        store = TutorConversationStoreDB(uid)
        conv = store.get(conv_id)
        if not conv:
            return jsonify({"error": "Not found"}), 404
        return jsonify({"conversation": conv})

    # ══════════════════════════════════════════════════════════════════
    # ─── COMPOUND AI ORCHESTRATOR ─────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════

    @app.route("/api/ai/chat", methods=["POST"])
    @login_required
    def api_ai_chat():
        """Unified AI chat endpoint — routes through the orchestrator."""
        uid = current_user_id()
        data = request.get_json(force=True)
        message = data.get("message", "")
        context = data.get("context", {})
        conversation_id = data.get("conversation_id")

        if not message:
            return jsonify({"error": "Message is required"}), 400

        try:
            from orchestrator import Orchestrator
            orch = Orchestrator(user_id=uid, rag_engine=get_engine())
        except Exception:
            from orchestrator import Orchestrator
            orch = Orchestrator(user_id=uid)

        # Get conversation history if conversation_id provided
        messages = []
        if conversation_id:
            store = TutorConversationStoreDB(uid)
            conv = store.get(conversation_id)
            if conv:
                messages = conv.get("messages", [])
                # Inherit subject/topic from conversation if not in context
                if not context.get("subject"):
                    context["subject"] = conv.get("subject", "")
                if not context.get("topic"):
                    context["topic"] = conv.get("topic", "")

        intent = orch.classify_intent(message, context)
        response = orch.route(intent, message, context, messages)

        # Save to conversation if conversation_id provided
        if conversation_id:
            store = TutorConversationStoreDB(uid)
            store.add_message(conversation_id, "user", message)
            store.add_message(conversation_id, "assistant", response.content)

        return jsonify({
            "response": response.content,
            "intent": intent,
            "agent": response.agent,
            "confidence": response.confidence,
            "metadata": response.metadata,
            "follow_up": response.follow_up,
        })

    @app.route("/api/knowledge-graph/<subject>")
    @login_required
    def api_knowledge_graph(subject):
        """Return mastery map + prerequisite graph for visualization."""
        uid = current_user_id()
        try:
            from knowledge_graph import SyllabusGraph
            graph = SyllabusGraph(subject)
            mastery_map = graph.get_mastery_map(uid)
            prerequisites = {}
            for topic_id in mastery_map:
                prerequisites[topic_id] = graph.get_prerequisites(topic_id)
            return jsonify({
                "subject": subject,
                "mastery_map": mastery_map,
                "prerequisites": prerequisites,
            })
        except (ImportError, Exception) as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/recommended-topics/<subject>")
    @login_required
    def api_recommended_topics(subject):
        """Return ordered list of what to study next based on KG."""
        uid = current_user_id()
        try:
            from knowledge_graph import SyllabusGraph
            graph = SyllabusGraph(subject)
            recommended = graph.get_recommended_next(uid)
            return jsonify({
                "subject": subject,
                "recommended": recommended,
            })
        except (ImportError, Exception) as e:
            return jsonify({"error": str(e)}), 500

    # ══════════════════════════════════════════════════════════════════
    # ─── DIFFERENTIATOR FEATURES ──────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════

    # ── Feature 1: ECF & Handwriting Vision ────────────────────────────

    @app.route("/api/ai/analyze-handwriting", methods=["POST"])
    @login_required
    def api_analyze_handwriting():
        """Analyze handwritten work with ECF marking."""
        uid = current_user_id()

        if "image" not in request.files:
            return jsonify({"error": "Image file is required"}), 400

        image_file = request.files["image"]
        image_data = image_file.read()
        if not image_data:
            return jsonify({"error": "Empty image file"}), 400

        question = request.form.get("question", "")
        subject = request.form.get("subject", "Mathematics")
        marks = int(request.form.get("marks", 4))
        command_term = request.form.get("command_term", "")

        try:
            from agents.vision_agent import VisionAgent
            agent = VisionAgent()
            result = agent.analyze_handwriting(
                image_data=image_data,
                question=question,
                subject=subject,
                marks=marks,
                command_term=command_term,
                user_id=uid,
            )
            return jsonify({
                "response": result.content,
                "agent": result.agent,
                "confidence": result.confidence,
                "metadata": result.metadata,
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ── Feature 2: Oral Exam Roleplay ─────────────────────────────────

    @app.route("/api/oral/start", methods=["POST"])
    @login_required
    def api_oral_start():
        """Start an oral exam practice session."""
        uid = current_user_id()
        data = request.get_json(force=True)

        try:
            from agents.oral_exam_agent import OralExamAgent
            agent = OralExamAgent(get_engine())
            result = agent.start_session(
                subject=data.get("subject", "English A"),
                text_title=data.get("text_title", ""),
                text_extract=data.get("text_extract", ""),
                global_issue=data.get("global_issue", ""),
                level=data.get("level", "HL"),
                user_id=uid,
            )
            return jsonify({
                "response": result.content,
                "session_id": result.metadata.get("session_id"),
                "session_state": result.metadata.get("session_state"),
                "phase": result.metadata.get("phase"),
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/oral/respond", methods=["POST"])
    @login_required
    def api_oral_respond():
        """Submit student transcript and get examiner response."""
        uid = current_user_id()
        data = request.get_json(force=True)
        transcript = data.get("transcript", "")
        session_state = data.get("session_state", {})
        session_id = data.get("session_id")

        if not transcript:
            return jsonify({"error": "Transcript is required"}), 400

        try:
            from agents.oral_exam_agent import OralExamAgent
            agent = OralExamAgent(get_engine())
            result = agent.listen_and_respond(
                transcript=transcript,
                session_state=session_state,
                user_id=uid,
                session_id=session_id,
            )
            return jsonify({
                "response": result.content,
                "session_state": result.metadata.get("session_state"),
                "phase": result.metadata.get("phase"),
                "claims_count": result.metadata.get("claims_count"),
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/oral/grade", methods=["POST"])
    @login_required
    def api_oral_grade():
        """Grade a completed oral session."""
        uid = current_user_id()
        data = request.get_json(force=True)
        session_state = data.get("session_state", {})
        session_id = data.get("session_id")

        try:
            from agents.oral_exam_agent import OralExamAgent
            agent = OralExamAgent(get_engine())
            result = agent.grade_oral(
                session_state=session_state,
                user_id=uid,
                session_id=session_id,
            )
            return jsonify({
                "response": result.content,
                "criterion_scores": result.metadata.get("criterion_scores"),
                "total_score": result.metadata.get("total_score"),
                "total_possible": result.metadata.get("total_possible"),
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/oral/history")
    @login_required
    def api_oral_history():
        """List past oral practice sessions."""
        uid = current_user_id()
        try:
            from database import get_db
            db = get_db()
            rows = db.execute(
                "SELECT id, subject, level, text_title, global_issue, "
                "total_score, started_at, completed_at "
                "FROM oral_sessions WHERE user_id = ? "
                "ORDER BY started_at DESC LIMIT 20",
                (uid,),
            ).fetchall()
            return jsonify({"sessions": [dict(r) for r in rows]})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ── Feature 3: Coursework IDE ─────────────────────────────────────

    @app.route("/api/coursework/check-feasibility", methods=["POST"])
    @login_required
    def api_coursework_feasibility():
        """Check coursework topic feasibility."""
        uid = current_user_id()
        data = request.get_json(force=True)

        try:
            from agents.coursework_ide_agent import CourseworkIDEAgent
            agent = CourseworkIDEAgent(get_engine())
            result = agent.check_feasibility(
                topic_proposal=data.get("topic", ""),
                subject=data.get("subject", ""),
                doc_type=data.get("doc_type", "ia"),
                school_constraints=data.get("school_constraints", ""),
            )
            return jsonify({
                "response": result.content,
                "feasibility_score": result.metadata.get("feasibility_score"),
                "verdict": result.metadata.get("verdict"),
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/coursework/analyze-data", methods=["POST"])
    @login_required
    def api_coursework_analyze_data():
        """Analyze experimental data with statistical tests."""
        uid = current_user_id()
        data = request.get_json(force=True)

        try:
            from agents.coursework_ide_agent import CourseworkIDEAgent
            agent = CourseworkIDEAgent(get_engine())
            result = agent.analyze_data(
                raw_data=data.get("data", ""),
                subject=data.get("subject", ""),
                hypothesis=data.get("hypothesis", ""),
                user_id=uid,
                session_id=data.get("session_id"),
            )
            return jsonify({
                "response": result.content,
                "has_computed_results": result.metadata.get("has_computed_results"),
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/coursework/review-draft", methods=["POST"])
    @login_required
    def api_coursework_review_draft():
        """Review a coursework draft with incremental feedback."""
        uid = current_user_id()
        data = request.get_json(force=True)

        try:
            from agents.coursework_ide_agent import CourseworkIDEAgent
            agent = CourseworkIDEAgent(get_engine())
            result = agent.review_draft(
                text=data.get("text", ""),
                doc_type=data.get("doc_type", "ia"),
                subject=data.get("subject", ""),
                criterion=data.get("criterion", ""),
                previous_feedback=data.get("previous_feedback"),
                version=int(data.get("version", 1)),
                user_id=uid,
                session_id=data.get("session_id"),
            )
            return jsonify({
                "response": result.content,
                "word_count": result.metadata.get("word_count"),
                "version": result.metadata.get("version"),
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/coursework/sessions/<int:session_id>")
    @login_required
    def api_coursework_session(session_id):
        """Get a coursework session with feedback history."""
        uid = current_user_id()
        try:
            from database import get_db
            db = get_db()
            session = db.execute(
                "SELECT * FROM coursework_sessions WHERE id = ? AND user_id = ?",
                (session_id, uid),
            ).fetchone()
            if not session:
                return jsonify({"error": "Session not found"}), 404

            drafts = db.execute(
                "SELECT * FROM coursework_drafts WHERE session_id = ? ORDER BY version",
                (session_id,),
            ).fetchall()

            analyses = db.execute(
                "SELECT * FROM data_analyses WHERE session_id = ? ORDER BY created_at",
                (session_id,),
            ).fetchall()

            return jsonify({
                "session": dict(session),
                "drafts": [dict(d) for d in drafts],
                "analyses": [dict(a) for a in analyses],
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ── Feature 5: Parametric Question Generation ─────────────────────

    @app.route("/api/questions/generate-parametric", methods=["POST"])
    @login_required
    def api_generate_parametric():
        """Generate verified parametric question variants."""
        data = request.get_json(force=True)

        try:
            from agents.question_gen_agent import QuestionGenAgent
            agent = QuestionGenAgent(get_engine())
            result = agent.generate_parametric(
                subject=data.get("subject", "Mathematics"),
                topic=data.get("topic", ""),
                source_question=data.get("source_question", ""),
                variation_type=data.get("variation_type", "numbers"),
                count=int(data.get("count", 3)),
                difficulty=data.get("difficulty_level", "medium"),
            )
            return jsonify({
                "response": result.content,
                "questions": result.metadata.get("questions", []),
                "total_generated": result.metadata.get("total_generated"),
                "total_verified": result.metadata.get("total_verified"),
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ── Feature 6: Executive Function & Study Planning ────────────────

    @app.route("/api/executive/daily-briefing")
    @login_required
    def api_daily_briefing():
        """Get today's personalized study briefing."""
        uid = current_user_id()
        try:
            from agents.executive_agent import ExecutiveAgent
            agent = ExecutiveAgent(get_engine())
            result = agent.daily_briefing(uid)
            return jsonify({
                "response": result.content,
                "burnout_risk": result.metadata.get("burnout_risk"),
                "burnout_signals": result.metadata.get("burnout_signals"),
                "priority_subjects": result.metadata.get("priority_subjects"),
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/executive/generate-plan", methods=["POST"])
    @login_required
    def api_generate_plan():
        """Generate an optimized study plan."""
        uid = current_user_id()
        data = request.get_json(force=True)
        try:
            from agents.executive_agent import ExecutiveAgent
            agent = ExecutiveAgent(get_engine())
            result = agent.generate_smart_plan(
                user_id=uid,
                days_ahead=int(data.get("days_ahead", 7)),
                daily_minutes=int(data.get("daily_minutes", 180)),
            )
            return jsonify({
                "response": result.content,
                "days_ahead": result.metadata.get("days_ahead"),
                "deadlines": result.metadata.get("deadlines"),
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/executive/reprioritize", methods=["POST"])
    @login_required
    def api_reprioritize():
        """Adjust study plan for changed deadlines."""
        uid = current_user_id()
        data = request.get_json(force=True)
        event = data.get("event", "")
        if not event:
            return jsonify({"error": "Event description is required"}), 400
        try:
            from agents.executive_agent import ExecutiveAgent
            agent = ExecutiveAgent(get_engine())
            result = agent.reprioritize(uid, event)
            return jsonify({
                "response": result.content,
                "event": result.metadata.get("event"),
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/executive/burnout-check")
    @login_required
    def api_burnout_check():
        """Check burnout risk assessment."""
        uid = current_user_id()
        try:
            from agents.executive_agent import ExecutiveAgent
            agent = ExecutiveAgent()
            burnout = agent.detect_burnout(uid)
            return jsonify(burnout)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ══════════════════════════════════════════════════════════════════
    # ─── COMMUNITY ANALYTICS (Step 13) ───────────────────────────────
    # ══════════════════════════════════════════════════════════════════

    @app.route("/community-analytics")
    def community_analytics_page():
        return render_template("analytics.html", show_sidebar=True,
                               profile=None, gam=None)

    @app.route("/api/analytics/global")
    def api_analytics_global():
        try:
            from community_analytics import global_stats
            return jsonify(global_stats())
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/analytics/trending")
    def api_analytics_trending():
        try:
            from community_analytics import trending_topics
            return jsonify({"topics": trending_topics()})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ══════════════════════════════════════════════════════════════════
    # ─── IMAGE UPLOAD / CAMERA (Step 14) ─────────────────────────────
    # ══════════════════════════════════════════════════════════════════
    # Handled by extending existing /api/upload — see ingest.py updates

    # ══════════════════════════════════════════════════════════════════
    # ─── CREDITS & TOKEN ECONOMY ────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════

    @app.route("/api/credits/balance")
    @login_required
    def api_credits_balance():
        uid = current_user_id()
        from credit_store import CreditStoreDB
        store = CreditStoreDB(uid)
        return jsonify({
            "balance": store.balance(),
            "transactions": store.transaction_history(limit=20),
        })

    @app.route("/api/credits/purchase", methods=["POST"])
    @login_required
    def api_credits_purchase():
        data = request.get_json()
        amount = int(data.get("amount", 0))
        if amount <= 0:
            return jsonify({"error": "Invalid amount"}), 400
        uid = current_user_id()
        from credit_store import CreditStoreDB
        store = CreditStoreDB(uid)
        result = store.credit(amount, "purchase", f"Purchased {amount} credits")
        return jsonify(result)

    # ══════════════════════════════════════════════════════════════════
    # ─── SUBSCRIPTION TIERS ─────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════

    @app.route("/api/subscription/current")
    @login_required
    def api_subscription_current():
        uid = current_user_id()
        from subscription_store import SubscriptionStoreDB
        store = SubscriptionStoreDB(uid)
        plan = store.current_plan()
        limits = store.plan_limits()
        return jsonify({"plan": plan, "limits": limits})

    @app.route("/api/subscription/upgrade", methods=["POST"])
    @login_required
    def api_subscription_upgrade():
        data = request.get_json()
        plan_id = data.get("plan_id", "")
        if not plan_id:
            return jsonify({"error": "Plan ID required"}), 400
        uid = current_user_id()
        from subscription_store import SubscriptionStoreDB
        store = SubscriptionStoreDB(uid)
        try:
            store.upgrade(plan_id)
            return jsonify({"success": True, "plan": store.current_plan()})
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    # ══════════════════════════════════════════════════════════════════
    # ─── SOS DETECTION & TUTORING ───────────────────────────────────
    # ══════════════════════════════════════════════════════════════════

    @app.route("/api/sos/status")
    @login_required
    def api_sos_status():
        uid = current_user_id()
        from sos_detector import SOSDetector
        detector = SOSDetector(uid)
        return jsonify({"alerts": detector.active_alerts()})

    @app.route("/api/sos/request-session", methods=["POST"])
    @login_required
    def api_sos_request_session():
        data = request.get_json()
        alert_id = int(data.get("alert_id", 0))
        if not alert_id:
            return jsonify({"error": "Alert ID required"}), 400
        uid = current_user_id()
        from sos_detector import SOSDetector
        detector = SOSDetector(uid)
        result = detector.request_session(alert_id)
        if not result["success"]:
            status = 402 if "credits" in result.get("error", "").lower() else 400
            return jsonify(result), status
        return jsonify(result)

    @app.route("/api/sos/tutor-context/<int:request_id>")
    @teacher_required
    def api_sos_tutor_context(request_id):
        from sos_detector import SOSDetector
        req = SOSDetector.get_tutor_request(request_id)
        if not req:
            return jsonify({"error": "Request not found"}), 404
        return jsonify(req)

    @app.route("/api/sos/complete/<int:request_id>", methods=["POST"])
    @teacher_required
    def api_sos_complete(request_id):
        uid = current_user_id()
        from sos_detector import SOSDetector
        SOSDetector.complete_session(request_id, uid)
        return jsonify({"success": True})

    # ══════════════════════════════════════════════════════════════════
    # ─── EXAMINER REVIEW PIPELINE ──────────────────────────────────
    # ══════════════════════════════════════════════════════════════════

    @app.route("/api/reviews/submit", methods=["POST"])
    @login_required
    def api_reviews_submit():
        data = request.get_json()
        doc_type = data.get("doc_type", "")
        subject = data.get("subject", "")
        title = data.get("title", "")
        text = data.get("text", "")
        if not all([doc_type, subject, text]):
            return jsonify({"error": "doc_type, subject, and text are required"}), 400
        uid = current_user_id()
        from examiner_pipeline import ExaminerPipeline
        pipeline = ExaminerPipeline()
        result = pipeline.submit_for_review(uid, doc_type, subject, title, text)
        if not result["success"]:
            return jsonify(result), 402
        return jsonify(result)

    @app.route("/api/reviews/mine")
    @login_required
    def api_reviews_mine():
        uid = current_user_id()
        from examiner_pipeline import ExaminerPipeline
        reviews = ExaminerPipeline.student_reviews(uid)
        return jsonify({"reviews": reviews})

    @app.route("/api/reviews/queue")
    @teacher_required
    def api_reviews_queue():
        from examiner_pipeline import ExaminerPipeline
        reviews = ExaminerPipeline.pending_reviews()
        return jsonify({"reviews": reviews})

    @app.route("/api/reviews/<int:review_id>/assign", methods=["POST"])
    @teacher_required
    def api_reviews_assign(review_id):
        uid = current_user_id()
        from examiner_pipeline import ExaminerPipeline
        ExaminerPipeline.assign_to_examiner(review_id, uid)
        return jsonify({"success": True})

    @app.route("/api/reviews/<int:review_id>/complete", methods=["POST"])
    @teacher_required
    def api_reviews_complete(review_id):
        data = request.get_json()
        feedback = data.get("feedback", "")
        grade = data.get("grade", "")
        video_url = data.get("video_url", "")
        if not feedback:
            return jsonify({"error": "Feedback required"}), 400
        from examiner_pipeline import ExaminerPipeline
        ExaminerPipeline.submit_examiner_feedback(review_id, feedback, grade, video_url)
        ExaminerPipeline.deliver_to_student(review_id)
        return jsonify({"success": True})

    @app.route("/api/reviews/<int:review_id>")
    @login_required
    def api_reviews_detail(review_id):
        uid = current_user_id()
        from examiner_pipeline import ExaminerPipeline
        review = ExaminerPipeline.get_review(review_id)
        if not review:
            return jsonify({"error": "Review not found"}), 404
        # Auth gate: student or assigned examiner
        if review["user_id"] != uid and review.get("examiner_id") != uid:
            if getattr(current_user, "role", "student") not in ("teacher", "admin"):
                abort(403)
        return jsonify(review)

    # ══════════════════════════════════════════════════════════════════
    # ─── TEACHER BATCH GRADING ──────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════

    @app.route("/api/teacher/batch-grade", methods=["POST"])
    @teacher_required
    def api_teacher_batch_grade():
        data = request.get_json()
        class_id = int(data.get("class_id", 0))
        subject = data.get("subject", "")
        doc_type = data.get("doc_type", "ia")
        assignment_title = data.get("assignment_title", "")
        submissions = data.get("submissions", [])
        if not class_id or not subject or not submissions:
            return jsonify({"error": "class_id, subject, and submissions required"}), 400

        uid = current_user_id()

        # Verify teacher owns the class
        cls = ClassStoreDB.get(class_id)
        if not cls or cls["teacher_id"] != uid:
            abort(404)

        # Deduct credits per student
        from credit_store import CreditStoreDB, FEATURE_COSTS
        cost_per = FEATURE_COSTS.get("batch_grade_per_student", 20)
        total_cost = cost_per * len(submissions)
        store = CreditStoreDB(uid)
        if not store.has_credits(total_cost):
            return jsonify({
                "error": "Insufficient credits",
                "required": total_cost,
                "balance": store.balance(),
            }), 402
        store.debit(total_cost, "batch_grade_per_student",
                    f"Batch grade: {len(submissions)} students")

        # Create job record
        from database import get_db as _get_db
        db = _get_db()
        now = datetime.now().isoformat()
        cur = db.execute(
            "INSERT INTO batch_grading_jobs "
            "(teacher_id, class_id, assignment_title, subject, doc_type, "
            "status, total_submissions, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'processing', ?, ?)",
            (uid, class_id, assignment_title, subject, doc_type,
             len(submissions), now),
        )
        job_id = cur.lastrowid
        db.commit()

        # Process batch
        try:
            from agents.batch_grading_agent import BatchGradingAgent
            agent = BatchGradingAgent()
            result = agent.process_batch(submissions, subject, doc_type)

            # Update job with results
            metadata = result.metadata or {}
            db.execute(
                "UPDATE batch_grading_jobs SET status = 'completed', "
                "processed_count = ?, results = ?, class_summary = ?, "
                "completed_at = ? WHERE id = ?",
                (metadata.get("processed", 0),
                 json.dumps(metadata.get("results", [])),
                 json.dumps(metadata.get("class_summary", {})),
                 datetime.now().isoformat(), job_id),
            )
            db.commit()

            return jsonify({
                "job_id": job_id,
                "status": "completed",
                "results": metadata.get("results", []),
                "class_summary": metadata.get("class_summary", {}),
            })
        except Exception as e:
            db.execute(
                "UPDATE batch_grading_jobs SET status = 'failed' WHERE id = ?",
                (job_id,),
            )
            db.commit()
            return jsonify({"error": str(e), "job_id": job_id}), 500

    @app.route("/api/teacher/batch-grade/<int:job_id>")
    @teacher_required
    def api_teacher_batch_grade_status(job_id):
        uid = current_user_id()
        from database import get_db as _get_db
        db = _get_db()
        row = db.execute(
            "SELECT * FROM batch_grading_jobs WHERE id = ? AND teacher_id = ?",
            (job_id, uid),
        ).fetchone()
        if not row:
            return jsonify({"error": "Job not found"}), 404
        result = dict(row)
        for key in ("results", "class_summary"):
            try:
                result[key] = json.loads(result[key])
            except (json.JSONDecodeError, TypeError):
                pass
        return jsonify(result)

    @app.route("/api/teacher/batch-grade/history")
    @teacher_required
    def api_teacher_batch_grade_history():
        uid = current_user_id()
        from database import get_db as _get_db
        db = _get_db()
        rows = db.execute(
            "SELECT id, class_id, assignment_title, subject, doc_type, status, "
            "total_submissions, processed_count, created_at, completed_at "
            "FROM batch_grading_jobs WHERE teacher_id = ? "
            "ORDER BY created_at DESC",
            (uid,),
        ).fetchall()
        return jsonify({"jobs": [dict(r) for r in rows]})

    # ══════════════════════════════════════════════════════════════════
    # ─── ENHANCED PARENT PORTAL ─────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════

    @app.route("/api/parent/traffic-light/<token>")
    def api_parent_traffic_light(token):
        parent_config = ParentConfigDB.load_by_token(token)
        if not parent_config or not parent_config.enabled:
            return jsonify({"error": "Invalid or disabled parent link"}), 404
        from parent_analytics import ParentAnalytics
        analytics = ParentAnalytics(parent_config.user_id)
        result = analytics.traffic_light()
        result["sos_highlights"] = analytics.sos_highlights()
        result["action_items"] = analytics.action_items()
        return jsonify(result)

    @app.route("/api/parent/digest/<token>")
    def api_parent_digest(token):
        parent_config = ParentConfigDB.load_by_token(token)
        if not parent_config or not parent_config.enabled:
            return jsonify({"error": "Invalid or disabled parent link"}), 404
        from parent_analytics import ParentAnalytics
        analytics = ParentAnalytics(parent_config.user_id)
        return jsonify(analytics.weekly_digest())

    # ══════════════════════════════════════════════════════════════════
    # ─── ADMISSIONS PROFILE & AGENT ─────────────────────────────────
    # ══════════════════════════════════════════════════════════════════

    @app.route("/api/admissions/profile")
    @login_required
    def api_admissions_profile():
        uid = current_user_id()
        # Check for existing profile
        from database import get_db as _get_db
        db = _get_db()
        row = db.execute(
            "SELECT * FROM admissions_profiles WHERE user_id = ?",
            (uid,),
        ).fetchone()
        if row:
            result = dict(row)
            for key in ("subject_strengths", "recommended_universities"):
                try:
                    result[key] = json.loads(result[key])
                except (json.JSONDecodeError, TypeError):
                    pass
            return jsonify(result)
        # Generate new profile
        from agents.admissions_agent import AdmissionsAgent
        agent = AdmissionsAgent()
        response = agent.generate_profile(uid)
        return jsonify({
            "profile": response.metadata.get("profile", {}),
            "content": response.content,
        })

    @app.route("/api/admissions/personal-statement", methods=["POST"])
    @login_required
    def api_admissions_personal_statement():
        data = request.get_json()
        target = data.get("target", "common_app")
        word_limit = int(data.get("word_limit", 650))
        uid = current_user_id()

        # Deduct credits
        from credit_store import CreditStoreDB, FEATURE_COSTS
        store = CreditStoreDB(uid)
        cost = FEATURE_COSTS.get("personal_statement", 200)
        if not store.has_credits(cost):
            return jsonify({
                "error": "Insufficient credits",
                "required": cost,
                "balance": store.balance(),
            }), 402
        store.debit(cost, "personal_statement", f"Personal statement: {target}")

        from agents.admissions_agent import AdmissionsAgent
        agent = AdmissionsAgent()
        response = agent.draft_personal_statement(uid, target, word_limit)
        return jsonify({
            "statement": response.content,
            "metadata": response.metadata,
        })

    @app.route("/api/admissions/suggest-universities", methods=["POST"])
    @login_required
    def api_admissions_suggest_universities():
        data = request.get_json()
        preferences = data.get("preferences", {})
        uid = current_user_id()
        from agents.admissions_agent import AdmissionsAgent
        agent = AdmissionsAgent()
        response = agent.suggest_universities(uid, preferences)
        return jsonify({
            "suggestions": response.metadata.get("suggestions", {}),
            "content": response.content,
        })

    # ── Start push notification scheduler (non-blocking) ─────────────
    if not app.config.get("TESTING"):
        try:
            from push import init_scheduler
            init_scheduler(app)
        except Exception:
            pass

    return app


if __name__ == "__main__":
    create_app().run(debug=True, port=5001)
