"""IB lifecycle routes — EE, IA, TOK, CAS pages and APIs."""

from __future__ import annotations

from datetime import date

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import login_required

from helpers import current_user_id
from extensions import EngineManager
from db_stores import IBLifecycleDB, StudentProfileDB
from lifecycle import CASReflection, CAS_LEARNING_OUTCOMES
from subject_config import get_subject_config

bp = Blueprint("lifecycle", __name__)


@bp.route("/lifecycle")
@login_required
def lifecycle_page():
    uid = current_user_id()
    profile = StudentProfileDB.load(uid)
    if not profile:
        return redirect(url_for("core.onboarding"))

    lifecycle = IBLifecycleDB(uid)
    return render_template(
        "lifecycle.html",
        profile=profile,
        lifecycle=lifecycle,
        summary=lifecycle.summary(),
        cas_outcomes=CAS_LEARNING_OUTCOMES,
    )


@bp.route("/lifecycle/ee")
@login_required
def lifecycle_ee():
    uid = current_user_id()
    profile = StudentProfileDB.load(uid)
    if not profile:
        return redirect(url_for("core.onboarding"))
    lifecycle = IBLifecycleDB(uid)
    return render_template("lifecycle.html", profile=profile, lifecycle=lifecycle,
                           summary=lifecycle.summary(), cas_outcomes=CAS_LEARNING_OUTCOMES,
                           section="ee")


@bp.route("/lifecycle/ia/<subject>")
@login_required
def lifecycle_ia(subject):
    uid = current_user_id()
    profile = StudentProfileDB.load(uid)
    if not profile:
        return redirect(url_for("core.onboarding"))
    lifecycle = IBLifecycleDB(uid)
    ia = lifecycle.get_ia_for_subject(subject)
    config = get_subject_config(subject)
    return render_template("lifecycle.html", profile=profile, lifecycle=lifecycle,
                           summary=lifecycle.summary(), cas_outcomes=CAS_LEARNING_OUTCOMES,
                           section="ia", ia_subject=subject, ia=ia,
                           ia_config=config)


@bp.route("/lifecycle/tok")
@login_required
def lifecycle_tok():
    uid = current_user_id()
    profile = StudentProfileDB.load(uid)
    if not profile:
        return redirect(url_for("core.onboarding"))
    lifecycle = IBLifecycleDB(uid)
    return render_template("lifecycle.html", profile=profile, lifecycle=lifecycle,
                           summary=lifecycle.summary(), cas_outcomes=CAS_LEARNING_OUTCOMES,
                           section="tok")


@bp.route("/lifecycle/cas")
@login_required
def lifecycle_cas():
    uid = current_user_id()
    profile = StudentProfileDB.load(uid)
    if not profile:
        return redirect(url_for("core.onboarding"))
    lifecycle = IBLifecycleDB(uid)
    return render_template("lifecycle.html", profile=profile, lifecycle=lifecycle,
                           summary=lifecycle.summary(), cas_outcomes=CAS_LEARNING_OUTCOMES,
                           section="cas")


@bp.route("/api/lifecycle/milestone", methods=["POST"])
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


@bp.route("/api/lifecycle/cas", methods=["POST"])
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


@bp.route("/api/lifecycle/update", methods=["POST"])
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


@bp.route("/api/lifecycle/draft-feedback", methods=["POST"])
@login_required
def api_draft_feedback():
    data = request.get_json()
    draft_text = data.get("text", "").strip()
    section = data.get("section", "")
    subject = data.get("subject", "")

    if not draft_text or not section:
        return jsonify({"error": "text and section are required"}), 400

    try:
        engine = EngineManager.get_engine()

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


@bp.route("/api/lifecycle/rq-check", methods=["POST"])
@login_required
def api_rq_check():
    data = request.get_json()
    rq = data.get("research_question", "").strip()
    subject = data.get("subject", "")

    if not rq:
        return jsonify({"error": "research_question is required"}), 400

    try:
        engine = EngineManager.get_engine()
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
