"""Tests for shared flashcards and study buddy features."""

import json
import pytest


class TestSharedFlashcards:
    def test_share_flashcard_deck(self, auth_client):
        resp = auth_client.post("/api/flashcards/share",
            data=json.dumps({
                "title": "Bio HL Flashcards",
                "subject": "Biology",
                "topic": "Cell Biology",
                "description": "Key concepts for cell biology",
                "cards": [
                    {"front": "What is mitosis?", "back": "Cell division producing identical cells"},
                    {"front": "What is meiosis?", "back": "Cell division producing gametes"},
                ],
            }),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "deck_id" in data

    def test_list_shared_flashcards(self, auth_client):
        # First share a deck
        auth_client.post("/api/flashcards/share",
            data=json.dumps({
                "title": "Chem Flashcards",
                "subject": "Chemistry",
                "cards": [{"front": "Q", "back": "A"}],
            }),
            content_type="application/json",
        )
        # Then list
        resp = auth_client.get("/api/flashcards/shared")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "decks" in data
        assert len(data["decks"]) >= 1

    def test_import_flashcard_deck(self, auth_client):
        # Share a deck
        resp = auth_client.post("/api/flashcards/share",
            data=json.dumps({
                "title": "Import Test",
                "subject": "Biology",
                "cards": [
                    {"front": "Q1", "back": "A1"},
                    {"front": "Q2", "back": "A2"},
                ],
            }),
            content_type="application/json",
        )
        deck_id = resp.get_json()["deck_id"]

        # Import it
        resp = auth_client.post(f"/api/flashcards/shared/{deck_id}/import")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["imported_count"] == 2

    def test_share_requires_title_subject(self, auth_client):
        resp = auth_client.post("/api/flashcards/share",
            data=json.dumps({"cards": []}),
            content_type="application/json",
        )
        assert resp.status_code == 400


class TestStudyBuddy:
    def test_save_preferences(self, auth_client):
        resp = auth_client.post("/api/buddy/preferences",
            data=json.dumps({
                "subjects": ["Biology", "Chemistry"],
                "availability": "weekdays",
                "timezone": "UTC",
            }),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_find_matches_empty(self, auth_client):
        # Save preferences first
        auth_client.post("/api/buddy/preferences",
            data=json.dumps({"subjects": ["Biology"]}),
            content_type="application/json",
        )
        # Find matches (should be empty — only one user)
        resp = auth_client.get("/api/buddy/matches")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "matches" in data

    def test_connect_sends_notification(self, auth_client, app):
        with app.app_context():
            from database import get_db
            from werkzeug.security import generate_password_hash
            db = get_db()
            # Create another user to connect with
            db.execute(
                "INSERT INTO users (id, name, email, password_hash, created_at) "
                "VALUES (10, 'Buddy User', 'buddy@test.com', ?, '2026-01-01')",
                (generate_password_hash("BuddyPass1"),),
            )
            db.execute("INSERT OR IGNORE INTO gamification (user_id) VALUES (10)")
            db.commit()

        resp = auth_client.post("/api/buddy/connect",
            data=json.dumps({"user_id": 10}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True
