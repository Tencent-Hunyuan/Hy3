"""Tests for domain models: dict / json / markdown round-trips."""
from __future__ import annotations

import json

from ctxpilot.models import (
    Decision,
    HandoffExport,
    Message,
    ProjectStateSnapshot,
    SessionTranscript,
    TaskItem,
)


def _sample_snapshot() -> ProjectStateSnapshot:
    return ProjectStateSnapshot(
        generated_at="2026-07-15T20:00:00Z",
        generator="hy3",
        project_map="src/ctxpilot/core.py is the facade",
        goals=["Ship MVP", "Write README"],
        tasks=[
            TaskItem("Build scaffold", "done", "pyproject + dirs"),
            TaskItem("Wire Hy3", "in_progress", "client done, need retry"),
            TaskItem("Fix drift bug", "blocked", "waiting on upstream"),
        ],
        decisions=[
            Decision("Use Python not Rust", "Faster vibe-coding, stdlib covers needs", "2026-07-15"),
        ],
        open_issues=["opencode adapter format may change"],
        conventions="Use absolute paths; no bare commands",
        raw={"note": "from test"},
    )


def test_message_roundtrip():
    m = Message(role="user", content="hi", tokens=3, ts="t1")
    d = m.to_dict()
    assert d["role"] == "user"
    assert Message.from_dict(d).content == "hi"


def test_snapshot_dict_roundtrip():
    snap = _sample_snapshot()
    restored = ProjectStateSnapshot.from_dict(snap.to_dict())
    assert restored.goals == snap.goals
    assert restored.tasks[1].status == "in_progress"
    assert restored.decisions[0].title == "Use Python not Rust"
    assert restored.raw == {"note": "from test"}


def test_snapshot_markdown_roundtrip():
    snap = _sample_snapshot()
    md = snap.to_markdown()
    assert "# HANDOFF" in md
    assert "[in_progress] Wire Hy3" in md
    assert "Use Python not Rust" in md
    restored = ProjectStateSnapshot.from_markdown(md)
    # markdown round-trip keeps the human-readable fields
    assert "Build scaffold" in [t.title for t in restored.tasks]
    assert restored.tasks[1].status == "in_progress"
    assert any("Rust" in d.title for d in restored.decisions)
    assert "opencode adapter format may change" in restored.open_issues


def test_handoff_export_json_roundtrip(tmp_path):
    exp = HandoffExport(source_agent="opencode", snapshot=_sample_snapshot(), meta={"v": 1})
    p = tmp_path / "out.handoff.json"
    exp.to_file(p)
    loaded = HandoffExport.from_file(p)
    assert loaded.source_agent == "opencode"
    assert loaded.snapshot is not None
    assert loaded.snapshot.goals == ["Ship MVP", "Write README"]
    # also via raw json string
    same = HandoffExport.from_json(exp.to_json())
    assert same.meta == {"v": 1}


def test_session_transcript_roundtrip():
    st = SessionTranscript(
        agent="codex",
        session_id="abc",
        messages=[Message("user", "do x")],
        token_usage=42,
        files_touched=["a.py"],
    )
    assert SessionTranscript.from_dict(st.to_dict()).agent == "codex"
