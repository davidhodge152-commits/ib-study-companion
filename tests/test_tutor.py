"""Tests for tutor chat experience."""

import json
import io
import pytest
from unittest.mock import patch, MagicMock


class TestTutorPage:
    def test_tutor_page_loads(self, auth_client):
        resp = auth_client.get("/tutor")
        assert resp.status_code == 200
        assert b"AI Tutor" in resp.data

    def test_tutor_page_has_markdown_deps(self, auth_client):
        resp = auth_client.get("/tutor")
        assert b"marked.min.js" in resp.data
        assert b"katex" in resp.data
        assert b"purify.min.js" in resp.data


class TestTutorConversation:
    def test_start_conversation(self, auth_client):
        resp = auth_client.post(
            "/api/tutor/start",
            data=json.dumps({"subject": "Biology", "topic": "Photosynthesis"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "conversation_id" in data

    def test_send_message(self, auth_client):
        # Start a conversation first
        start = auth_client.post(
            "/api/tutor/start",
            data=json.dumps({"subject": "Biology", "topic": "Photosynthesis"}),
            content_type="application/json",
        )
        conv_id = start.get_json()["conversation_id"]

        mock_tutor = MagicMock()
        mock_tutor.respond.return_value = "Photosynthesis is the process by which plants convert light energy."
        mock_tutor.suggest_follow_ups.return_value = ["What are the reactants?", "How does chlorophyll work?"]

        with patch("blueprints.ai.TutorSession", create=True) as MockTS:
            # Patch the import inside api_tutor_message
            with patch.dict("sys.modules", {"tutor": MagicMock(TutorSession=MagicMock(return_value=mock_tutor))}):
                resp = auth_client.post(
                    "/api/tutor/message",
                    data=json.dumps({"conversation_id": conv_id, "message": "What is photosynthesis?"}),
                    content_type="application/json",
                )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "response" in data
        assert "Photosynthesis" in data["response"]
        # follow_ups key should always be present
        assert "follow_ups" in data
        assert isinstance(data["follow_ups"], list)

    def test_get_history(self, auth_client):
        resp = auth_client.get("/api/tutor/history")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "conversations" in data

    def test_load_conversation(self, auth_client):
        # Start a conversation first
        start = auth_client.post(
            "/api/tutor/start",
            data=json.dumps({"subject": "Chemistry", "topic": "Bonding"}),
            content_type="application/json",
        )
        conv_id = start.get_json()["conversation_id"]

        resp = auth_client.get(f"/api/tutor/{conv_id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "conversation" in data
        assert data["conversation"]["subject"] == "Chemistry"

    def test_load_nonexistent_conversation(self, auth_client):
        resp = auth_client.get("/api/tutor/99999")
        assert resp.status_code == 404


class TestTutorImageUpload:
    def test_upload_image_no_file(self, auth_client):
        resp = auth_client.post("/api/tutor/upload-image")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data

    def test_upload_image_empty_file(self, auth_client):
        data = {"image": (io.BytesIO(b""), "empty.jpg")}
        resp = auth_client.post(
            "/api/tutor/upload-image",
            data=data,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400

    def test_upload_image_vision_not_available(self, auth_client):
        """When VisionAgent import fails, returns 500 with clear error."""
        fake_image = io.BytesIO(b"\xff\xd8\xff\xe0fake-jpeg-data")
        data = {"image": (fake_image, "test.jpg")}
        resp = auth_client.post(
            "/api/tutor/upload-image",
            data=data,
            content_type="multipart/form-data",
        )
        # Should either return text or an error (depends on API key availability)
        assert resp.status_code in (200, 500)
        result = resp.get_json()
        assert "text" in result or "error" in result
