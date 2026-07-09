"""
Vector Store — ChromaDB-backed semantic search for the QA phase.

IMPORTANT: chromadb and sentence-transformers are lazy-loaded.
The server starts without them; they're only imported when QA is used.
Install with: pip install chromadb sentence-transformers --break-system-packages
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

_embedding_model: Any = None
_chroma_client: Any = None


def _get_chromadb():
    global _chroma_client
    if _chroma_client is None:
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            settings = get_settings()
            persist_dir = Path(settings.chroma_persist_dir)
            persist_dir.mkdir(parents=True, exist_ok=True)
            _chroma_client = chromadb.PersistentClient(
                path=str(persist_dir),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        except ImportError:
            raise RuntimeError(
                "chromadb is not installed. Run: pip install chromadb --break-system-packages"
            )
    return _chroma_client


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            settings = get_settings()
            logger.info("Loading embedding model: %s", settings.embedding_model)
            _embedding_model = SentenceTransformer(
                settings.embedding_model,
                device=settings.embedding_device,
            )
        except ImportError:
            raise RuntimeError(
                "sentence-transformers is not installed. "
                "Run: pip install sentence-transformers --break-system-packages"
            )
    return _embedding_model


class VectorStore:
    """ChromaDB-backed vector store for code snippet semantic search."""

    def __init__(self):
        self._client = _get_chromadb()
        self._collection_name = "code_snippets"
        self._collection: Any = None
        self._get_or_create_collection()

    def _get_or_create_collection(self):
        try:
            self._collection = self._client.get_collection(self._collection_name)
        except Exception:
            self._collection = self._client.create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        logger.info("Vector store ready: %d documents", self._collection.count())

    def index_snippets(
        self, repo_name: str, snippets: list[dict[str, Any]], *, batch_size: int = 32
    ) -> int:
        if not snippets:
            return 0
        model = _get_embedding_model()
        total = 0
        for i in range(0, len(snippets), batch_size):
            batch = snippets[i:i + batch_size]
            ids, documents, metadatas, embeddings = [], [], [], []
            for snippet in batch:
                snippet_id = hashlib.md5(
                    f"{repo_name}:{snippet['path']}:{i}".encode()
                ).hexdigest()[:16]
                text = f"File: {snippet['path']}\n{snippet['content']}"
                if len(text) > 8000:
                    text = text[:8000]
                embedding = model.encode(text, normalize_embeddings=True).tolist()
                ids.append(snippet_id)
                documents.append(text)
                embeddings.append(embedding)
                metadatas.append({
                    "repo": repo_name, "path": snippet["path"],
                    "lines": snippet.get("lines", 0),
                    "language": snippet.get("language", ""),
                    **(snippet.get("metadata", {}) or {}),
                })
            try:
                self._collection.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
                total += len(batch)
            except Exception as e:
                logger.warning("Failed to index batch: %s", e)
        logger.info("Indexed %d snippets for repo: %s", total, repo_name)
        return total

    def search(self, query: str, repo_name: str | None = None, top_k: int = 15) -> list[dict[str, Any]]:
        model = _get_embedding_model()
        query_embedding = model.encode(query, normalize_embeddings=True).tolist()
        where_filter = {"repo": repo_name} if repo_name else None
        try:
            results = self._collection.query(
                query_embeddings=[query_embedding], n_results=top_k, where=where_filter,
            )
        except Exception as e:
            logger.warning("Vector search failed: %s", e)
            return []
        if not results or not results.get("ids") or not results["ids"][0]:
            return []
        return [
            {
                "id": results["ids"][0][i],
                "path": results["metadatas"][0][i].get("path", ""),
                "content": results["documents"][0][i] if results.get("documents") else "",
                "score": 1.0 - results["distances"][0][i] if results.get("distances") else 0.0,
                "metadata": results["metadatas"][0][i],
            }
            for i in range(len(results["ids"][0]))
        ]

    def clear_repo(self, repo_name: str) -> int:
        try:
            results = self._collection.get(where={"repo": repo_name})
            if results and results["ids"]:
                self._collection.delete(ids=results["ids"])
                count = len(results["ids"])
                logger.info("Cleared %d snippets for repo: %s", count, repo_name)
                return count
        except Exception as e:
            logger.warning("Clear repo failed: %s", e)
        return 0

    @property
    def count(self) -> int:
        return self._collection.count()


_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
