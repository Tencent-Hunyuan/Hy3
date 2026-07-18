"""
Vector store - ChromaDB persistence layer with a local ONNX embedding function.

ChromaDB requires an embedding function object. We wrap our ONNX embedder in
_LocalEmbeddingFunction so no external embedding service is needed. Search can
be scoped to a subset of documents via `source_filters` (a ChromaDB `where`).
"""
import logging
from typing import List, Optional, Dict, Any

import chromadb

import config
from embedder import create_embedder
from text_chunker import Chunk

logger = logging.getLogger(__name__)


class _LocalEmbeddingFunction:
    """Adapter satisfying ChromaDB's EmbeddingFunction interface (chromadb>=0.4.16).

    chromadb now expects ``__call__(self, input)`` (a list of texts) and a
    ``name()`` method, plus ``get_config`` / ``build_from_config`` for
    persistence. The legacy ``embed_documents``/``embed_queries`` are kept for
    backwards compatibility but are no longer invoked by chromadb.
    """

    def __init__(self):
        self._embedder = create_embedder()

    @property
    def dimension(self) -> int:
        return self._embedder.dimension

    def __call__(self, input: List[str]) -> List[List[float]]:
        return self._embedder.embed(input)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._embedder.embed(texts)

    def embed_queries(self, texts: List[str]) -> List[List[float]]:
        return self._embedder.embed(texts)

    def embed_query(self, input: List[str]) -> List[List[float]]:
        # chromadb 1.x calls embed_query() on the query path.
        return self._embedder.embed(input)

    def name(self) -> str:
        # ChromaDB 1.x calls name() to detect embedding-function conflicts.
        return "hy3_local_onnx"

    def get_config(self) -> dict:
        return {"name": self.name()}

    @classmethod
    def build_from_config(cls, config: dict):
        return cls()


class VectorStore:
    def __init__(
        self,
        collection_name: str = "hy3_rag",
        persist_dir=None,
    ):
        self.embedder = create_embedder()
        self.client = chromadb.PersistentClient(
            path=str(persist_dir or config.CHROMA_DIR)
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=_LocalEmbeddingFunction(),
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "Vector store ready: %d chunks in collection '%s'",
            self.collection.count(),
            collection_name,
        )

    def add_documents(self, chunks: List[Chunk]):
        if not chunks:
            return
        ids = [c.chunk_id for c in chunks]
        docs = [c.text for c in chunks]
        metadatas = [
            {"doc_name": c.doc_name, "index": c.index, "length": c.length}
            for c in chunks
        ]
        self.collection.add(ids=ids, documents=docs, metadatas=metadatas)
        logger.info("Added %d chunks to vector store", len(chunks))

    def search(
        self,
        query: str,
        top_k: int = 6,
        source_filters: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        where = None
        if source_filters:
            where = {"doc_name": {"$in": source_filters}}

        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        out = []
        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]
        for i, doc in enumerate(docs):
            dist = dists[i] if i < len(dists) else 1.0
            # ChromaDB cosine distance -> similarity score in [0, 1]
            score = max(0.0, 1.0 - float(dist))
            out.append(
                {
                    "text": doc,
                    "doc_name": metas[i].get("doc_name") if metas[i] else None,
                    "index": metas[i].get("index") if metas[i] else i,
                    "score": round(score, 4),
                }
            )
        return out

    def count(self) -> int:
        return self.collection.count()

    def delete_document(self, filename: str):
        self.collection.delete(where={"doc_name": filename})
        logger.info("Deleted document from vector store: %s", filename)

    def get_all_documents(self) -> List[Dict[str, Any]]:
        """Return distinct document names with their chunk counts."""
        try:
            res = self.collection.get(include=["metadatas"])
        except Exception:
            return []
        metas = res.get("metadatas", []) or []
        docs: Dict[str, int] = {}
        for m in metas:
            if not m:
                continue
            name = m.get("doc_name")
            if name:
                docs[name] = docs.get(name, 0) + 1
        return [{"filename": k, "chunk_count": v} for k, v in docs.items()]
