"""Flashcard CRUD and review routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import login_required

from helpers import current_user_id
from profile import Flashcard, XP_AWARDS
from db_stores import FlashcardDeckDB, GamificationProfileDB, StudentProfileDB

bp = Blueprint("flashcards", __name__)


@bp.route("/flashcards")
@login_required
def flashcards_page():
    uid = current_user_id()
    profile = StudentProfileDB.load(uid)
    if not profile:
        return redirect(url_for("core.onboarding"))
    fc_deck = FlashcardDeckDB(uid)
    return render_template("flashcards.html", profile=profile,
                           due_count=fc_deck.due_count(),
                           total_cards=len(fc_deck.cards))


@bp.route("/api/flashcards")
@login_required
def api_flashcards():
    uid = current_user_id()
    fc_deck = FlashcardDeckDB(uid)
    subject = request.args.get("subject", "")
    mode = request.args.get("mode", "due")

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


@bp.route("/api/flashcards/review", methods=["POST"])
@login_required
def api_flashcard_review():
    data = request.get_json()
    card_id = data.get("card_id", "")
    rating = int(data.get("rating", 3))

    if not card_id or rating not in (1, 2, 3, 4):
        return jsonify({"error": "card_id and rating (1-4) required"}), 400

    uid = current_user_id()
    fc_deck = FlashcardDeckDB(uid)
    fc_deck.review(card_id, rating)

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


@bp.route("/api/flashcards/create", methods=["POST"])
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


@bp.route("/api/flashcards/<card_id>", methods=["DELETE"])
@login_required
def api_flashcard_delete(card_id):
    uid = current_user_id()
    fc_deck = FlashcardDeckDB(uid)
    if fc_deck.delete(card_id):
        return jsonify({"success": True})
    return jsonify({"error": "Card not found"}), 404
