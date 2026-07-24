"""Shared test fixtures: a fake Hy3 client and sample data factories."""
from __future__ import annotations

from ctxpilot.ingestion import RawMaterial
from ctxpilot.models import Message, SessionTranscript


class FakeHy3:
    """Minimal stand-in for Hy3Client.chat(); returns scripted text."""

    def __init__(self, responses: list[str] | None = None, default: str = "ok"):
        self._responses = list(responses or [])
        self.default = default
        self.calls: list[tuple] = []

    def chat(self, user: str, system: str | None = None, reasoning_effort: str | None = None,
             temperature: float | None = None, top_p: float | None = None) -> str:
        self.calls.append((user, system, reasoning_effort))
        if self._responses:
            return self._responses.pop(0)
        return self.default


SAMPLE_MARKDOWN = """# HANDOFF — Project State Snapshot

> Generated: 2026-07-15T20:00:00Z | Generator: hy3

## Project Map
src/ctxpilot/core.py is the facade.

## Current Goals
- Ship MVP
- Write README

## Tasks
- [done] Build scaffold
- [in_progress] Wire Hy3
- [blocked] Fix drift bug

## Decisions
- **Use Python not Rust**: Faster vibe-coding (2026-07-15)

## Open Issues
- opencode adapter format may change

## Conventions
Use absolute paths.
"""


def make_raw(project_path: str = "/tmp/proj") -> RawMaterial:
    tr = SessionTranscript(
        agent="opencode",
        session_id="s1",
        messages=[Message("user", "refactor core"), Message("assistant", "done", tokens=120)],
        token_usage=200,
        files_touched=["src/ctxpilot/core.py"],
    )
    return RawMaterial(
        project_path=project_path,
        git={"branch": "main", "recent_commits": ["abc feat"], "status": [], "diff_stat": ""},
        transcripts=[tr],
    )
