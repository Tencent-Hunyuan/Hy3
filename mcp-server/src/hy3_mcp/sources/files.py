# Copyright 2026 Tencent Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Data source #1 — sandboxed local file access with deterministic retrieval.

Security model: every user-supplied path is resolved (following symlinks)
and must stay inside the sandbox root (``HY3_MCP_ROOT``); anything else is
rejected with a clean :class:`ToolError`.  Files are size-capped and decoded
as UTF-8 with replacement, so hostile input can never crash the server.

Retrieval is a pure function: chunking by headings/blank lines, scoring by
keyword overlap (ASCII words + CJK unigrams/bigrams), deterministic
tie-breaking — the same question over the same corpus always returns the
same chunks in the same order.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from mcp.server.fastmcp.exceptions import ToolError

__all__ = [
    "Chunk",
    "ScoredChunk",
    "SafeFileReader",
    "chunk_text",
    "rank_chunks",
]

_WORD_RE = re.compile(r"[a-z0-9_]+")
_CJK_RUN_RE = re.compile(r"[一-鿿]+")


@dataclass(frozen=True)
class Chunk:
    """One retrievable slice of a document."""

    source: str  # sandbox-relative path of the file
    chunk_id: int
    text: str


@dataclass(frozen=True)
class ScoredChunk:
    chunk: Chunk
    score: int


class SafeFileReader:
    """Read-only file access confined to a sandbox root directory.

    ``extra_roots`` admits additional allowed directories (e.g. an
    explicitly configured absolute ``HY3_MCP_DOCS_DIR`` outside the main
    root).  Traversal and symlink escapes out of *every* allowed root are
    still rejected — paths are resolved first and must land inside one of
    the allowed roots.
    """

    def __init__(
        self,
        root: Path,
        max_bytes: int = 512_000,
        extra_roots: Sequence[Path] = (),
    ) -> None:
        self.root = root.resolve()
        self.max_bytes = max_bytes
        self.extra_roots = tuple(r.resolve() for r in extra_roots)

    @property
    def _allowed_roots(self) -> tuple[Path, ...]:
        return (self.root, *self.extra_roots)

    def resolve(self, user_path: str) -> Path:
        """Resolve ``user_path`` and reject anything escaping the sandbox."""
        if not str(user_path).strip():
            raise ToolError("empty path: provide a path relative to the sandbox root")
        p = Path(user_path)
        candidate = (p if p.is_absolute() else self.root / p).resolve()
        if not any(candidate.is_relative_to(r) for r in self._allowed_roots):
            allowed = ", ".join(str(r) for r in self._allowed_roots)
            raise ToolError(
                f"path escapes sandbox root: {user_path!r} resolves outside "
                f"{allowed} (set HY3_MCP_ROOT to widen the sandbox)"
            )
        return candidate

    def read_text(self, user_path: str) -> str:
        """Read a sandboxed file as UTF-8 text (size-capped, never crashes)."""
        path = self.resolve(user_path)
        if not path.is_file():
            raise ToolError(f"file not found inside the sandbox: {user_path!r}")
        size = path.stat().st_size
        if size > self.max_bytes:
            raise ToolError(
                f"file too large: {user_path!r} is {size} bytes "
                f"(limit {self.max_bytes}); pass a smaller excerpt"
            )
        return path.read_bytes().decode("utf-8", errors="replace")

    def relative(self, path: Path) -> str:
        for r in self._allowed_roots:
            if path.is_relative_to(r):
                return str(path.relative_to(r))
        return str(path)

    def list_docs(
        self,
        sub: str | None = None,
        exts: Sequence[str] = (".md", ".txt", ".rst"),
        limit: int = 200,
    ) -> list[Path]:
        """List document files under ``sub`` (sandbox-relative), sorted, capped."""
        base = self.resolve(sub) if sub else self.root
        if not base.is_dir():
            raise ToolError(f"not a directory inside the sandbox: {sub!r}")
        lowered = tuple(e.lower() for e in exts)
        found = sorted(
            p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in lowered
        )
        return found[:limit]


def _tokens(text: str) -> set[str]:
    """Deterministic token set: ASCII words + CJK unigrams and bigrams."""
    low = text.lower()
    toks = set(_WORD_RE.findall(low))
    for run in _CJK_RUN_RE.findall(low):
        toks.update(run)
        toks.update(a + b for a, b in zip(run, run[1:]))
    return toks


def chunk_text(text: str, source: str, max_chars: int = 800) -> list[Chunk]:
    """Split ``text`` into chunks along headings/blank lines, <= max_chars."""
    blocks: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.startswith("#") or (not line.strip() and current):
            if current:
                blocks.append("\n".join(current).strip())
                current = []
        if line.strip():
            current.append(line)
    if current:
        blocks.append("\n".join(current).strip())

    chunks: list[Chunk] = []
    buf = ""
    for block in blocks:
        if not block:
            continue
        while len(block) > max_chars:  # hard-split oversized blocks
            head, block = block[:max_chars], block[max_chars:]
            if buf:
                chunks.append(Chunk(source, len(chunks), buf))
                buf = ""
            chunks.append(Chunk(source, len(chunks), head))
        if buf and len(buf) + len(block) + 1 > max_chars:
            chunks.append(Chunk(source, len(chunks), buf))
            buf = block
        else:
            buf = f"{buf}\n{block}".strip() if buf else block
    if buf:
        chunks.append(Chunk(source, len(chunks), buf))
    return chunks


def rank_chunks(
    question: str, chunks: Iterable[Chunk], top_k: int = 3
) -> list[ScoredChunk]:
    """Rank chunks by distinct-token overlap with the question (deterministic)."""
    q_tokens = _tokens(question)
    scored = [
        ScoredChunk(chunk=c, score=len(q_tokens & _tokens(c.text))) for c in chunks
    ]
    scored = [s for s in scored if s.score > 0]
    scored.sort(key=lambda s: (-s.score, s.chunk.source, s.chunk.chunk_id))
    return scored[: max(1, top_k)]
