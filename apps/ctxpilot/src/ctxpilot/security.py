"""Security layer (DESIGN.md §8).

S1  Secret scrubbing before anything leaves the machine (Hy3 call / HANDOFF.md write).
S3  Ensure HANDOFF.md and .env are git-ignored so they can't be committed by accident.
S5  Key only ever read from env / local .env (handled in config.py).
"""
from __future__ import annotations

import re
from pathlib import Path

# Order matters: broader patterns first.
# Quotes are expressed as \x22 (") and \x27 (') so the raw strings never contain
# a literal quote that would break Python string parsing.
_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z0-9 ]*PRIVATE KEY-----"),
        "[PRIVATE KEY REDACTED]",
    ),
    (re.compile(r"(sk-[A-Za-z0-9]{8,})"), r"sk-****"),
    (re.compile(r"(AKIA[0-9A-Z]{8,})"), r"AKIA****"),
    (re.compile(r"(?i)(api[_-]?key\s*[=:]\s*[\x22\x27]?)([A-Za-z0-9_\-]{6,})"), r"\1****"),
    (re.compile(r"(?i)(secret[_-]?key\s*[=:]\s*[\x22\x27]?)([A-Za-z0-9_\-]{6,})"), r"\1****"),
    (re.compile(r"(?i)(token\s*[=:]\s*[\x22\x27]?)([A-Za-z0-9_\-\.]{8,})"), r"\1****"),
    (re.compile(r"(?i)(password\s*[=:]\s*[\x22\x27]?)([^\s\x22\x27]{4,})"), r"\1****"),
    (re.compile(r"(?i)(Bearer\s+)([A-Za-z0-9_\-\.]{10,})"), r"\1****"),
]


def sanitize(text: str) -> str:
    """Redact likely secrets. Safe to call on any text before sending outward."""
    if not text:
        return text
    for pat, repl in _SECRET_PATTERNS:
        text = pat.sub(repl, text)
    return text


# Entries we always want ignored in a project that uses CtxPilot.
_GITIGNORE_ENTRIES = (".env", "HANDOFF.md", "*.handoff.json", ".ctxpilot/")


def ensure_gitignore(project_path: str | Path, extra: tuple[str, ...] = ()) -> bool:
    """Append CtxPilot ignore entries to <project_path>/.gitignore if missing.

    Returns True if anything was added, False if already present.
    """
    p = Path(project_path)
    p.mkdir(parents=True, exist_ok=True)
    gi = p / ".gitignore"
    existing_lines = gi.read_text(encoding="utf-8").splitlines() if gi.exists() else []
    existing = {ln.strip() for ln in existing_lines if ln.strip()}
    to_add = [e for e in (*_GITIGNORE_ENTRIES, *extra) if e not in existing]
    if not to_add:
        return False
    out = existing_lines[:]
    if out and out[-1] != "":
        out.append("")
    out.extend(to_add)
    out.append("")
    gi.write_text("\n".join(out), encoding="utf-8")
    return True
