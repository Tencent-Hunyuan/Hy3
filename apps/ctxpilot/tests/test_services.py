"""Tests for all service-layer use-cases (N2/N3/N4/N5/N6/N7)."""
from __future__ import annotations

from pathlib import Path

from ctxpilot.models import ProjectStateSnapshot
from ctxpilot.services import (
    BriefService,
    DriftService,
    HandoffService,
    MemoryService,
    SavingsService,
    SnapshotService,
)
from ctxpilot import security

from conftest import FakeHy3, SAMPLE_MARKDOWN, make_raw


# ---- N2 Snapshot ---------------------------------------------------------
def test_snapshot_build_parses_hy3_markdown():
    svc = SnapshotService()
    snap = svc.build(make_raw(), FakeHy3([SAMPLE_MARKDOWN]))
    assert "Ship MVP" in snap.goals
    assert snap.tasks[1].status == "in_progress"
    assert "Rust" in snap.decisions[0].title
    assert snap.generator == "hy3"


def test_snapshot_write_sanitizes_and_gitignores(tmp_path):
    svc = SnapshotService()
    snap = svc.build(make_raw(), FakeHy3([SAMPLE_MARKDOWN]))
    snap.project_map = "key=sk-abcdefghijklmnop secret"
    path = svc.write(snap, tmp_path)
    text = path.read_text()
    assert "sk-****" in text
    assert "sk-abcdefghijklmnop" not in text
    assert (tmp_path / ".gitignore").exists()


# ---- N4 Handoff ----------------------------------------------------------
def test_handoff_json_roundtrip(tmp_path):
    svc = HandoffService()
    snap = SnapshotService().build(make_raw(), FakeHy3([SAMPLE_MARKDOWN]))
    exp = svc.export(snap, source_agent="opencode")
    f = svc.to_file(exp, tmp_path / "x.handoff.json")
    prompt = svc.import_as_prompt(f, target_agent="codex")
    assert "for agent: codex" in prompt
    assert "Ship MVP" in prompt


def test_handoff_from_markdown_file(tmp_path):
    md = tmp_path / "HANDOFF.md"
    md.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
    prompt = HandoffService().import_as_prompt(md)
    assert "CONTEXT HANDOFF" in prompt
    assert "Wire Hy3" in prompt


# ---- N7 Brief ------------------------------------------------------------
def test_brief_generate():
    snap = SnapshotService().build(make_raw(), FakeHy3([SAMPLE_MARKDOWN]))
    out = BriefService().generate(snap, FakeHy3(default="BRIEF TEXT"))
    assert out == "BRIEF TEXT"


# ---- N3 Drift ------------------------------------------------------------
def test_drift_parse_and_red_flag():
    svc = DriftService()
    report = svc.analyze(
        make_raw(),
        FakeHy3(["red|loop|retrying same edit\nyellow|contradiction|switched approach"]),
    )
    assert report.has_red
    assert report.signals[0].kind == "loop"
    assert report.to_dict()["signals"][0]["severity"] == "red"


def test_drift_no_signals():
    report = DriftService().analyze(make_raw(), FakeHy3([""]))
    assert report.signals == []


# ---- N5 Memory -----------------------------------------------------------
def test_memory_exact_and_fallback():
    m = MemoryService()
    m.add("why python", "faster vibe-coding")
    assert "faster vibe-coding" in m.answer("why python")
    # unknown with hy3
    out = m.answer("why not rust", FakeHy3(default="rust is fine"))
    assert out == "rust is fine"


def test_memory_persists(tmp_path):
    p = tmp_path / "mem.txt"
    m = MemoryService(p)
    m.add("q1", "a1")
    m2 = MemoryService(p)
    assert m2.answer("q1") == "a1\n(source: local memory)"


# ---- N6 Savings ----------------------------------------------------------
def test_savings_estimate():
    raw = make_raw()
    snap = SnapshotService().build(raw, FakeHy3([SAMPLE_MARKDOWN]))
    res = SavingsService().estimate(raw, snapshot=snap, project_path="/tmp/proj")
    assert res["reread_tokens"] > res["snapshot_tokens"]
    assert res["saved_tokens"] > 0
    assert res["reduction_ratio"] > 1
