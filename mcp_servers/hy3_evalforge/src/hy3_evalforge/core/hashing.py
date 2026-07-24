"""Stable IDs and conservative text similarity for reproducible artifacts."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

_WHITESPACE = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    """Normalize Unicode and whitespace without changing the sequence of visible tokens."""
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFC", value)).strip()


def normalize_for_hash(value: Any) -> Any:
    """Convert Pydantic and JSON-like values into deterministic, normalized JSON data."""
    if isinstance(value, BaseModel):
        return normalize_for_hash(value.model_dump(mode="json"))
    if isinstance(value, str):
        return normalize_text(value)
    if isinstance(value, Mapping):
        return {str(key): normalize_for_hash(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [normalize_for_hash(item) for item in value]
    return value


def stable_id(prefix: str, value: Any) -> str:
    """Generate a short stable artifact identifier from canonical normalized JSON."""
    canonical = json.dumps(
        normalize_for_hash(value), ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def ngram_similarity(left: str, right: str, *, n: int = 3) -> float:
    """Return Jaccard similarity of normalized character n-grams for conservative de-duplication."""
    if n < 1:
        raise ValueError("n must be at least one")
    left_grams = _ngrams(normalize_text(left), n)
    right_grams = _ngrams(normalize_text(right), n)
    if not left_grams and not right_grams:
        return 1.0
    return len(left_grams & right_grams) / len(left_grams | right_grams)


def _ngrams(value: str, n: int) -> set[str]:
    if not value:
        return set()
    if len(value) <= n:
        return {value}
    return {value[index : index + n] for index in range(len(value) - n + 1)}
