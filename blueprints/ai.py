"""AI chat, tutor, oral, handwriting, coursework IDE, question gen, executive, admissions, knowledge graph routes."""

from __future__ import annotations

import json
import os

from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required

from helpers import current_user_id
from extensions import EngineManager
from db_stores import (
    GamificationProfileDB,
    StudentAbilityStoreDB,
    StudentProfileDB,
    TutorConversationStoreDB,
)

bp = Blueprint("ai", __name__)


# ── AI Tutor ──────────────────────────────────────────

@bp.route("/tutor")
@login_required
def tutor_page():
    from subject_config import get_syllabus_topics
    uid = current_user_id()
    profile = StudentProfileDB(uid)
    gam = GamificationProfileDB(uid)

    # Embed syllabus topics for enrolled subjects so JS can populate
    # the topic dropdown instantly without an extra API call.
    all_topics = {}
    for subj in profile.subjects:
        topics = get_syllabus_topics(subj.name)
        all_topics[subj.name] = [
            {"id": t.id, "name": t.name, "subtopics": t.subtopics, "hl_only": t.hl_only}
            for t in topics
        ]

    return render_template(
        "tutor.html", profile=profile, gam=gam,
        syllabus_topics=all_topics,
    )


@bp.route("/api/tutor/start", methods=["POST"])
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


@bp.route("/api/tutor/message", methods=["POST"])
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

    follow_ups = []
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
        try:
            follow_ups = tutor.suggest_follow_ups(response)
        except Exception:
            pass  # Follow-ups are optional
    except ImportError:
        response = "The AI tutor requires the Gemini API. Please configure your API key."
    except Exception as e:
        response = f"I encountered an issue: {str(e)}"

    store.add_message(conv_id, "assistant", response)
    return jsonify({"success": True, "response": response, "follow_ups": follow_ups})


@bp.route("/api/tutor/history")
@login_required
def api_tutor_history():
    from helpers import paginate_args, paginated_response

    uid = current_user_id()
    page, limit = paginate_args(default_limit=20)
    store = TutorConversationStoreDB(uid)
    convos = store.list_conversations(limit=limit * page)
    total = len(convos)
    start = (page - 1) * limit
    result = paginated_response(convos[start:start + limit], total, page, limit)
    result["conversations"] = result.pop("items")
    return jsonify(result)


@bp.route("/api/tutor/<int:conv_id>")
@login_required
def api_tutor_get(conv_id):
    uid = current_user_id()
    store = TutorConversationStoreDB(uid)
    conv = store.get(conv_id)
    if not conv:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"conversation": conv})


# ── Compound AI Orchestrator ──────────────────────────────

@bp.route("/api/ai/chat", methods=["POST"])
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
        orch = Orchestrator(user_id=uid, rag_engine=EngineManager.get_engine())
    except Exception:
        from orchestrator import Orchestrator
        orch = Orchestrator(user_id=uid)

    messages = []
    if conversation_id:
        store = TutorConversationStoreDB(uid)
        conv = store.get(conversation_id)
        if conv:
            messages = conv.get("messages", [])
            if not context.get("subject"):
                context["subject"] = conv.get("subject", "")
            if not context.get("topic"):
                context["topic"] = conv.get("topic", "")

    intent = orch.classify_intent(message, context)
    response = orch.route(intent, message, context, messages)

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


# ── Knowledge Graph ──────────────────────────────────────

@bp.route("/api/knowledge-graph/<subject>")
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


@bp.route("/api/recommended-topics/<subject>")
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


# ── Handwriting Vision Analysis ──────────────────────────────

@bp.route("/api/ai/analyze-handwriting", methods=["POST"])
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


# ── Oral Exam Roleplay ──────────────────────────────────────

@bp.route("/api/oral/start", methods=["POST"])
@login_required
def api_oral_start():
    """Start an oral exam practice session."""
    uid = current_user_id()
    data = request.get_json(force=True)

    try:
        from agents.oral_exam_agent import OralExamAgent
        agent = OralExamAgent(EngineManager.get_engine())
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


@bp.route("/api/oral/respond", methods=["POST"])
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
        agent = OralExamAgent(EngineManager.get_engine())
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


@bp.route("/api/oral/grade", methods=["POST"])
@login_required
def api_oral_grade():
    """Grade a completed oral session."""
    uid = current_user_id()
    data = request.get_json(force=True)
    session_state = data.get("session_state", {})
    session_id = data.get("session_id")

    try:
        from agents.oral_exam_agent import OralExamAgent
        agent = OralExamAgent(EngineManager.get_engine())
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


@bp.route("/api/oral/history")
@login_required
def api_oral_history():
    """List past oral practice sessions."""
    from helpers import paginate_args, paginated_response

    uid = current_user_id()
    page, limit = paginate_args(default_limit=20)
    try:
        from database import get_db
        db = get_db()
        total_row = db.execute(
            "SELECT COUNT(*) FROM oral_sessions WHERE user_id = ?", (uid,)
        ).fetchone()
        total = total_row[0] if total_row else 0
        offset = (page - 1) * limit
        rows = db.execute(
            "SELECT id, subject, level, text_title, global_issue, "
            "total_score, started_at, completed_at "
            "FROM oral_sessions WHERE user_id = ? "
            "ORDER BY started_at DESC LIMIT ? OFFSET ?",
            (uid, limit, offset),
        ).fetchall()
        result = paginated_response([dict(r) for r in rows], total, page, limit)
        result["sessions"] = result.pop("items")
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Coursework IDE ──────────────────────────────────────────

@bp.route("/api/coursework/check-feasibility", methods=["POST"])
@login_required
def api_coursework_feasibility():
    """Check coursework topic feasibility."""
    uid = current_user_id()
    data = request.get_json(force=True)

    try:
        from agents.coursework_ide_agent import CourseworkIDEAgent
        agent = CourseworkIDEAgent(EngineManager.get_engine())
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


@bp.route("/api/coursework/analyze-data", methods=["POST"])
@login_required
def api_coursework_analyze_data():
    """Analyze experimental data with statistical tests."""
    uid = current_user_id()
    data = request.get_json(force=True)

    try:
        from agents.coursework_ide_agent import CourseworkIDEAgent
        agent = CourseworkIDEAgent(EngineManager.get_engine())
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


@bp.route("/api/coursework/review-draft", methods=["POST"])
@login_required
def api_coursework_review_draft():
    """Review a coursework draft with incremental feedback."""
    uid = current_user_id()
    data = request.get_json(force=True)

    try:
        from agents.coursework_ide_agent import CourseworkIDEAgent
        agent = CourseworkIDEAgent(EngineManager.get_engine())
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


@bp.route("/api/coursework/sessions/<int:session_id>")
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


# ── Parametric Question Generation ──────────────────────────

@bp.route("/api/questions/generate-parametric", methods=["POST"])
@login_required
def api_generate_parametric():
    """Generate verified parametric question variants."""
    data = request.get_json(force=True)

    try:
        from agents.question_gen_agent import QuestionGenAgent
        agent = QuestionGenAgent(EngineManager.get_engine())
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


# ── Executive Function & Study Planning ──────────────────────

@bp.route("/api/executive/daily-briefing")
@login_required
def api_daily_briefing():
    """Get today's personalized study briefing."""
    uid = current_user_id()
    try:
        from agents.executive_agent import ExecutiveAgent
        agent = ExecutiveAgent(EngineManager.get_engine())
        result = agent.daily_briefing(uid)
        return jsonify({
            "response": result.content,
            "burnout_risk": result.metadata.get("burnout_risk"),
            "burnout_signals": result.metadata.get("burnout_signals"),
            "priority_subjects": result.metadata.get("priority_subjects"),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/executive/generate-plan", methods=["POST"])
@login_required
def api_generate_plan():
    """Generate an optimized study plan."""
    uid = current_user_id()
    data = request.get_json(force=True)
    try:
        from agents.executive_agent import ExecutiveAgent
        agent = ExecutiveAgent(EngineManager.get_engine())
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


@bp.route("/api/executive/reprioritize", methods=["POST"])
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
        agent = ExecutiveAgent(EngineManager.get_engine())
        result = agent.reprioritize(uid, event)
        return jsonify({
            "response": result.content,
            "event": result.metadata.get("event"),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/executive/burnout-check")
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


# ── Admissions Agent ──────────────────────────────────────

@bp.route("/admissions")
@login_required
def admissions_page():
    uid = current_user_id()
    profile = StudentProfileDB(uid)
    gam = GamificationProfileDB(uid)
    return render_template("admissions.html", profile=profile, gam=gam)


@bp.route("/api/admissions/deadlines")
@login_required
def api_admissions_deadlines():
    uid = current_user_id()
    from database import get_db
    db = get_db()
    rows = db.execute(
        "SELECT * FROM admissions_deadlines WHERE user_id = ? ORDER BY deadline_date ASC",
        (uid,),
    ).fetchall()
    return jsonify({"deadlines": [dict(r) for r in rows]})


@bp.route("/api/admissions/deadlines", methods=["POST"])
@login_required
def api_admissions_add_deadline():
    uid = current_user_id()
    data = request.get_json(force=True)
    university = data.get("university", "")
    deadline_date = data.get("deadline_date", "")
    if not university or not deadline_date:
        return jsonify({"error": "University and deadline date are required"}), 400
    from database import get_db
    from datetime import datetime as dt
    db = get_db()
    cur = db.execute(
        "INSERT INTO admissions_deadlines (user_id, university, program, deadline_date, "
        "deadline_type, status, notes, created_at) VALUES (?, ?, ?, ?, ?, 'upcoming', ?, ?)",
        (uid, university, data.get("program", ""), deadline_date,
         data.get("deadline_type", "application"), data.get("notes", ""),
         dt.now().isoformat()),
    )
    db.commit()
    return jsonify({"success": True, "deadline_id": cur.lastrowid})


@bp.route("/api/admissions/deadlines/<int:deadline_id>", methods=["PUT"])
@login_required
def api_admissions_update_deadline(deadline_id):
    uid = current_user_id()
    data = request.get_json(force=True)
    from database import get_db
    db = get_db()
    row = db.execute(
        "SELECT id FROM admissions_deadlines WHERE id = ? AND user_id = ?",
        (deadline_id, uid),
    ).fetchone()
    if not row:
        return jsonify({"error": "Not found"}), 404

    updates = []
    params = []
    for field in ("status", "notes", "university", "program", "deadline_date", "deadline_type"):
        if field in data:
            updates.append(f"{field} = ?")
            params.append(data[field])
    if not updates:
        return jsonify({"error": "No fields to update"}), 400
    params.append(deadline_id)
    db.execute(f"UPDATE admissions_deadlines SET {', '.join(updates)} WHERE id = ?", params)
    db.commit()
    return jsonify({"success": True})


@bp.route("/api/admissions/profile")
@login_required
def api_admissions_profile():
    uid = current_user_id()
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
    from agents.admissions_agent import AdmissionsAgent
    agent = AdmissionsAgent()
    response = agent.generate_profile(uid)
    return jsonify({
        "profile": response.metadata.get("profile", {}),
        "content": response.content,
    })


@bp.route("/api/admissions/personal-statement", methods=["POST"])
@login_required
def api_admissions_personal_statement():
    data = request.get_json()
    target = data.get("target", "common_app")
    word_limit = int(data.get("word_limit", 650))
    uid = current_user_id()

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


@bp.route("/api/admissions/suggest-universities", methods=["POST"])
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


@bp.route("/api/tutor/upload-image", methods=["POST"])
@login_required
def api_tutor_upload_image():
    """Accept an image and extract text via OCR for the tutor chat."""
    if "image" not in request.files:
        return jsonify({"error": "Image file is required"}), 400

    image_file = request.files["image"]
    image_data = image_file.read()
    if not image_data:
        return jsonify({"error": "Empty image file"}), 400

    try:
        from agents.vision_agent import VisionAgent

        agent = VisionAgent()
        result = agent.extract_text(image_data)
        return jsonify({"text": result.content if hasattr(result, "content") else str(result)})
    except ImportError:
        return jsonify({"error": "Vision agent not available. Please configure your API key."}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── AI Feedback ──────────────────────────────────────────

@bp.route("/api/ai/feedback", methods=["POST"])
@login_required
def api_ai_feedback():
    """Record thumbs-up/thumbs-down feedback on an AI response."""
    uid = current_user_id()
    data = request.get_json(force=True)
    agent = data.get("agent", "")
    feedback_type = data.get("feedback_type", "")
    if feedback_type not in ("thumbs_up", "thumbs_down"):
        return jsonify({"error": "feedback_type must be 'thumbs_up' or 'thumbs_down'"}), 400
    if not agent:
        return jsonify({"error": "agent is required"}), 400

    from database import get_db
    from datetime import datetime as dt

    db = get_db()
    db.execute(
        "INSERT INTO ai_feedback (user_id, interaction_id, agent, feedback_type, "
        "comment, context, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            uid,
            data.get("interaction_id"),
            agent,
            feedback_type,
            data.get("comment", ""),
            json.dumps(data.get("context", {})),
            dt.now().isoformat(),
        ),
    )
    db.commit()
    return jsonify({"success": True})
