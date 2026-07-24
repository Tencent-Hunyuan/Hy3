"""N5 (phase 2) — MemoryService: lightweight project-memory Q&A (with citations).

Stores decision/context facts and answers "why did we choose X?" via Hy3, citing
the stored fact. Leverages Hy3's long context (256K) plus exact local recall.
"""
from __future__ import annotations

from pathlib import Path


class MemoryService:
    def __init__(self, store_path: str | Path | None = None):
        self.store_path = Path(store_path) if store_path else None
        self.facts: dict[str, str] = {}
        if self.store_path and self.store_path.exists():
            self._load()

    def add(self, question: str, answer: str) -> None:
        self.facts[question.strip()] = answer.strip()
        self._persist()

    def _persist(self) -> None:
        if not self.store_path:
            return
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text("\n".join(f"{q}\t{a}" for q, a in self.facts.items()), encoding="utf-8")

    def _load(self) -> None:
        for line in self.store_path.read_text(encoding="utf-8").splitlines():
            if "\t" in line:
                q, a = line.split("\t", 1)
                self.facts[q] = a

    def answer(self, question: str, hy3=None) -> str:
        q = question.strip()
        if q in self.facts:
            return f"{self.facts[q]}\n(source: local memory)"
        if hy3 is None:
            return "(no local answer and no Hy3 client provided)"
        context = "\n".join(f"Q: {q}\nA: {a}" for q, a in self.facts.items())
        prompt = f"Project memory:\n{context}\n\nQuestion: {q}\nAnswer concisely, citing memory if relevant."
        return hy3.chat(prompt)
