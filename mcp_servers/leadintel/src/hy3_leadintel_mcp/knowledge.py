from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path


SUPPORTED_SUFFIXES = {".md", ".txt", ".csv", ".json"}
TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


@dataclass(frozen=True)
class Citation:
    path: str
    score: int
    excerpt: str


def tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text) if len(token) > 1}


def safe_child(root: Path, child: str | Path) -> Path:
    root = root.expanduser().resolve()
    path = (root / child).expanduser().resolve() if not Path(child).is_absolute() else Path(child).expanduser().resolve()
    if path != root and root not in path.parents:
        raise ValueError(f"path escapes HY3_LEADINTEL_ROOT: {child}")
    return path


def read_text_file(path: Path, max_chars: int = 20000) -> str:
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        return "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)[:max_chars]
    return path.read_text(encoding="utf-8", errors="replace")[:max_chars]


def query_documents(root: Path, docs_dir: str | Path, question: str, top_k: int = 4) -> list[Citation]:
    directory = safe_child(root, docs_dir)
    if not directory.exists() or not directory.is_dir():
        raise ValueError(f"knowledge base directory does not exist: {docs_dir}")

    q_tokens = tokenize(question)
    scored: list[Citation] = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        text = read_text_file(path)
        tokens = tokenize(text)
        overlap = q_tokens & tokens
        if not overlap:
            continue
        excerpt = make_excerpt(text, overlap)
        scored.append(Citation(path=str(path.relative_to(root)), score=len(overlap), excerpt=excerpt))

    return sorted(scored, key=lambda item: (-item.score, item.path))[: max(1, min(top_k, 8))]


def make_excerpt(text: str, terms: set[str], width: int = 420) -> str:
    lowered = text.lower()
    first = min((lowered.find(term) for term in terms if lowered.find(term) >= 0), default=0)
    start = max(0, first - width // 3)
    excerpt = " ".join(text[start : start + width].split())
    return excerpt
