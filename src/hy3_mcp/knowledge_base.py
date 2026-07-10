"""Knowledge base: chunking, indexing and persistence.

Chunks parsed documents, builds a BM25 index over them, and persists the
index to a JSON file so the knowledge base survives server restarts.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from typing import Optional

from .config import Settings
from .parsers import ParsedDocument, parse_file, iter_supported_paths
from .retrievers import BM25Index, tokenize


@dataclass
class Chunk:
    chunk_id: str
    source: str
    text: str


@dataclass
class KnowledgeBaseState:
    chunks: list[Chunk] = field(default_factory=list)
    version: int = 1


class KnowledgeBase:
    """Persistent, retrievable knowledge base backed by BM25."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.chunks: list[Chunk] = []
        self._index = BM25Index()
        self._seq = 0
        self.load()

    # ----- persistence -------------------------------------------------
    def load(self) -> None:
        path = self.settings.kb_store_path
        if not os.path.isfile(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self.chunks = [Chunk(**c) for c in data.get("chunks", [])]
            # rebuild index
            self._index = BM25Index()
            self._index.add_documents([tokenize(c.text) for c in self.chunks])
            self._seq = len(self.chunks)
        except (json.JSONDecodeError, KeyError, TypeError):
            # Corrupt store: start fresh rather than crashing the server.
            self.chunks = []

    def save(self) -> None:
        path = self.settings.kb_store_path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        state = KnowledgeBaseState(chunks=self.chunks)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(asdict(state), fh, ensure_ascii=False, indent=2)

    # ----- ingestion ---------------------------------------------------
    def _chunk_text(self, text: str, size: int = 800, overlap: int = 120) -> list[str]:
        text = text.strip()
        if not text:
            return []
        if len(text) <= size:
            return [text]
        chunks: list[str] = []
        start = 0
        step = max(1, size - overlap)
        while start < len(text):
            end = min(start + size, len(text))
            piece = text[start:end].strip()
            if piece:
                chunks.append(piece)
            if end == len(text):
                break
            start += step
        return chunks

    def add_documents(self, docs: list[ParsedDocument]) -> int:
        new_chunks: list[Chunk] = []
        tokenized: list[list[str]] = []
        for doc in docs:
            for piece in self._chunk_text(doc.content):
                self._seq += 1
                cid = f"c{self._seq}"
                new_chunks.append(Chunk(chunk_id=cid, source=doc.path, text=piece))
                tokenized.append(tokenize(piece))
        self.chunks.extend(new_chunks)
        if tokenized:
            self._index.add_documents(tokenized)
        self.save()
        return len(new_chunks)

    def load_paths(self, paths: list[str]) -> dict:
        """Resolve, parse and ingest a list of file/directory paths."""
        resolved = iter_supported_paths(paths)
        loaded = 0
        skipped = 0
        errors: list[str] = []
        docs: list[ParsedDocument] = []
        for p in resolved:
            try:
                docs.append(parse_file(p))
                loaded += 1
            except FileNotFoundError:
                errors.append(f"not found: {p}")
                skipped += 1
            except Exception as exc:  # pragma: no cover - defensive
                errors.append(f"{p}: {exc}")
                skipped += 1
        added = self.add_documents(docs) if docs else 0
        return {
            "files_loaded": loaded,
            "chunks_added": added,
            "skipped": skipped,
            "total_chunks": len(self.chunks),
            "errors": errors,
        }

    # ----- retrieval ---------------------------------------------------
    def search(self, query: str, top_k: int = 5) -> list[Chunk]:
        ranked = self._index.search(query, top_k=top_k)
        return [self.chunks[i] for i, _ in ranked]

    def is_empty(self) -> bool:
        return len(self.chunks) == 0
