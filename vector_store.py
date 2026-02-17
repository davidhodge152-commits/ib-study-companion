"""Vector store abstraction — wraps ChromaDB with a swappable interface.

Provides a protocol-based interface so the vector backend can be
replaced (e.g. with Pinecone, Qdrant) without changing RAG/ingest code.

Usage:
    from vector_store import get_vector_store
    store = get_vector_store()
    store.add(ids, documents, metadatas)
    results = store.query(query_texts, n_results, where)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger(__name__)

CHROMA_DIR = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "ib_documents"


class VectorStore(Protocol):
    """Protocol for vector store backends."""
    def add(self, ids: list[str], documents: list[str],
            metadatas: list[dict] | None = None) -> None: ...
    def query(self, query_texts: list[str], n_results: int = 5,
              where: dict | None = None) -> dict: ...
    def get(self, ids: list[str] | None = None,
            where: dict | None = None) -> dict: ...
    def delete(self, ids: list[str]) -> None: ...
    def count(self) -> int: ...


class ChromaDBStore:
    """Wraps chromadb.PersistentClient with lazy collection access."""

    def __init__(self, chroma_dir: str | Path | None = None,
                 collection_name: str = COLLECTION_NAME) -> None:
        self._chroma_dir = str(chroma_dir or CHROMA_DIR)
        self._collection_name = collection_name
        self._client = None
        self._collection = None

    def _get_collection(self):
        if self._collection is None:
            import chromadb
            self._client = chromadb.PersistentClient(path=self._chroma_dir)
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def add(self, ids: list[str], documents: list[str],
            metadatas: list[dict] | None = None) -> None:
        col = self._get_collection()
        kwargs: dict[str, Any] = {"ids": ids, "documents": documents}
        if metadatas:
            kwargs["metadatas"] = metadatas
        col.add(**kwargs)

    def query(self, query_texts: list[str], n_results: int = 5,
              where: dict | None = None) -> dict:
        col = self._get_collection()
        kwargs: dict[str, Any] = {
            "query_texts": query_texts,
            "n_results": n_results,
        }
        if where:
            kwargs["where"] = where
        return col.query(**kwargs)

    def get(self, ids: list[str] | None = None,
            where: dict | None = None) -> dict:
        col = self._get_collection()
        kwargs: dict[str, Any] = {}
        if ids:
            kwargs["ids"] = ids
        if where:
            kwargs["where"] = where
        return col.get(**kwargs)

    def delete(self, ids: list[str]) -> None:
        col = self._get_collection()
        col.delete(ids=ids)

    def count(self) -> int:
        col = self._get_collection()
        return col.count()


# Module-level singleton
_store: VectorStore | None = None


def get_vector_store(chroma_dir: str | Path | None = None,
                     collection_name: str = COLLECTION_NAME) -> VectorStore:
    """Factory function returning the vector store singleton."""
    global _store
    if _store is None:
        _store = ChromaDBStore(chroma_dir=chroma_dir, collection_name=collection_name)
    return _store


def reset_vector_store() -> None:
    """Reset the singleton (called after doc upload/delete)."""
    global _store
    _store = None
