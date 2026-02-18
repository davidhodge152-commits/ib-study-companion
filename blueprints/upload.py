"""Upload, documents, and delete document routes."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import login_required

from helpers import current_user_id, DATA_DIR, _analyze_writing_style
from extensions import EngineManager
from profile import XP_AWARDS
from db_stores import GamificationProfileDB, StudentProfileDB, UploadStoreDB

bp = Blueprint("upload", __name__)

# Magic byte signatures for file header validation
_MAGIC_BYTES = {
    ".pdf": b"%PDF",
    ".png": b"\x89PNG",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".webp": b"RIFF",
}


def _validate_file_header(file_storage, ext: str) -> bool:
    """Check file header magic bytes match the claimed extension."""
    expected = _MAGIC_BYTES.get(ext)
    if not expected:
        return False
    header = file_storage.read(len(expected))
    file_storage.seek(0)
    return header.startswith(expected)


@bp.route("/upload")
@login_required
def upload():
    uid = current_user_id()
    profile = StudentProfileDB.load(uid)
    if not profile:
        return redirect(url_for("core.onboarding"))
    uploads = UploadStoreDB(uid).load()
    return render_template("upload.html", profile=profile, uploads=uploads)


@bp.route("/api/upload", methods=["POST"])
@login_required
def api_upload():
    if os.environ.get("VERCEL"):
        return jsonify({
            "error": "File uploads are not available in the serverless deployment. "
                     "Please use the local version for document upload features."
        }), 501

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No filename provided"}), 400

    allowed_ext = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_ext:
        return jsonify({"error": f"Supported formats: PDF, PNG, JPG, WEBP"}), 400

    if not _validate_file_header(file, ext):
        return jsonify({"error": "File content does not match its extension."}), 400

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

    # Try background processing first, fall back to synchronous
    from tasks import enqueue, is_async_available

    if is_async_available():
        # Background: enqueue ingestion, return immediately
        from ingest import ingest_uploaded_file
        upload_id = uuid.uuid4().hex
        uid = current_user_id()

        # Record upload as "processing"
        upload_entry = {
            "id": upload_id,
            "filename": filename,
            "doc_type": doc_type,
            "subject": "",
            "level": "",
            "chunks": 0,
            "uploaded_at": datetime.now().isoformat(),
        }
        UploadStoreDB(uid).add(upload_entry)

        enqueue(
            ingest_uploaded_file,
            str(save_path),
            filename,
            doc_type,
            is_image,
        )

        gam = GamificationProfileDB(uid)
        gam.award_xp(XP_AWARDS["upload_document"], "upload_document")

        return jsonify({
            "success": True,
            "status": "processing",
            "upload_id": upload_id,
            "filename": filename,
        })

    # Synchronous fallback
    try:
        from ingest import ingest_uploaded_file
        result = ingest_uploaded_file(str(save_path), filename, doc_type, is_image)

        if not result.get("success"):
            return jsonify({"error": result.get("error", "Ingestion failed")}), 400

        EngineManager.reset()

    except Exception as e:
        logger.error("api_upload ingestion failed: %s", e, exc_info=True)
        return jsonify({"error": "Ingestion failed. Please try again."}), 500

    uid = current_user_id()
    upload_entry = {
        "id": uuid.uuid4().hex,
        "filename": filename,
        "doc_type": result["doc_type"],
        "subject": result["subject"],
        "level": result["level"],
        "chunks": result["chunks"],
        "uploaded_at": datetime.now().isoformat(),
    }
    UploadStoreDB(uid).add(upload_entry)

    if doc_type == "my_past_exam":
        try:
            _analyze_writing_style(result.get("text", ""))
        except Exception:
            pass

    gam = GamificationProfileDB(uid)
    gam.award_xp(XP_AWARDS["upload_document"], "upload_document")

    return jsonify({
        "success": True,
        "filename": filename,
        "doc_type": result["doc_type"],
        "subject": result["subject"],
        "level": result["level"],
        "chunks": result["chunks"],
    })


@bp.route("/documents")
@login_required
def documents():
    uid = current_user_id()
    profile = StudentProfileDB.load(uid)
    if not profile:
        return redirect(url_for("core.onboarding"))

    uploads = UploadStoreDB(uid).load()

    try:
        stats = EngineManager.get_engine().collection_stats()
    except Exception:
        stats = {"count": 0, "subjects": [], "doc_types": [], "sources": []}

    return render_template("documents.html", profile=profile, uploads=uploads, stats=stats)


@bp.route("/api/documents/<doc_id>", methods=["DELETE"])
@login_required
def api_delete_document(doc_id):
    uid = current_user_id()
    upload_store = UploadStoreDB(uid)
    target = upload_store.delete(doc_id)

    if not target:
        return jsonify({"error": "Document not found"}), 404

    try:
        import chromadb
        chroma_dir = Path(__file__).parent.parent / "chroma_db"
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

    EngineManager.reset()

    return jsonify({"success": True})
