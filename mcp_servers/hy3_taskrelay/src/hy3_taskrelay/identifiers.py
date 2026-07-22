"""Deterministic identifiers for portable TaskRelay artifacts."""

from __future__ import annotations

import hashlib
import json


def stable_content_id(prefix: str, value: object) -> str:
    """Return a stable, non-secret identifier derived from canonical JSON content."""

    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{prefix}_{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]}"
