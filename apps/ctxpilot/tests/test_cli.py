"""CLI tests via typer's test runner. Hy3.chat is patched so no network/key needed."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ctxpilot.cli import app

from conftest import SAMPLE_MARKDOWN

runner = CliRunner()


@pytest.fixture(autouse=True)
def _patch(monkeypatch):
    monkeypatch.setattr("ctxpilot.hy3.client.Hy3Client.chat", lambda self, *a, **k: SAMPLE_MARKDOWN)
    monkeypatch.setenv("HY3_API_KEY", "fake-key")
    monkeypatch.setenv("HY3_BASE_URL", "http://localhost:8000/v1")


def test_config_command():
    r = runner.invoke(app, ["config"])
    assert r.exit_code == 0
    assert "base_url" in r.stdout
    assert "has_credentials" in r.stdout


def test_snapshot_writes_handoff(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    r = runner.invoke(app, ["snapshot", str(proj)])
    assert r.exit_code == 0, r.stdout
    assert (proj / "HANDOFF.md").exists()
    assert (proj / ".gitignore").exists()


def test_export_then_import(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    r1 = runner.invoke(app, ["export", str(proj), "--out", str(tmp_path / "h.json")])
    assert r1.exit_code == 0, r1.stdout
    assert (tmp_path / "h.json").exists()
    r2 = runner.invoke(app, ["import-handoff", str(tmp_path / "h.json"), "--target", "codex"])
    assert r2.exit_code == 0, r2.stdout
    assert "CONTEXT HANDOFF" in r2.stdout


def test_brief_command(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    r = runner.invoke(app, ["brief", str(proj)])
    assert r.exit_code == 0
    # brief returns the patched SAMPLE_MARKDOWN content
    assert "HANDOFF" in r.stdout
