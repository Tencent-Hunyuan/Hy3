"""Tests for ingestion: fake git runner + a real temp git repo integration."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from ctxpilot.ingestion import RawMaterial, collect, git_collect


class _FakeSession:
    def __init__(self, agent, sid, files):
        self._agent = agent
        self._sid = sid
        self._files = files

    def discover_sessions(self):
        return [Path(f"/fake/{self._sid}")]

    def parse_session(self, path):
        from ctxpilot.models import SessionTranscript

        return SessionTranscript(
            agent=self._agent, session_id=self._sid, files_touched=self._files
        )


def _fake_runner(out: dict):
    def run(args):
        key = " ".join(args)
        if "rev-parse" in key:
            return subprocess.CompletedProcess(args, 0, "main\n")
        if "log" in key:
            return subprocess.CompletedProcess(args, 0, "abc feat\n\ndef fix\n")
        if "status" in key:
            return subprocess.CompletedProcess(args, 0, " M a.py\n")
        if "diff" in key:
            return subprocess.CompletedProcess(args, 0, " a.py | 2 +-\n")
        return subprocess.CompletedProcess(args, 0, "")

    return run


def test_collect_with_fake_git_and_adapters():
    ad = _FakeSession("opencode", "s1", ["a.py"])
    rm = collect("/tmp/proj", adapters=[ad], git_runner=_fake_runner({}))
    assert isinstance(rm, RawMaterial)
    assert rm.git["branch"] == "main"
    assert rm.git["recent_commits"] == ["abc feat", "def fix"]
    assert rm.transcripts[0].agent == "opencode"
    assert rm.transcripts[0].files_touched == ["a.py"]


def test_git_collect_handles_missing_repo():
    # non-git dir + default runner => graceful empty-ish result
    rm = git_collect(Path("/nonexistent/path/xyz"))
    assert "branch" in rm
    assert rm["recent_commits"] == []


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_collect_real_git_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "hello.txt").write_text("hi")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "init commit"], cwd=repo, check=True)

    rm = collect(repo, adapters=[], run_git=True)
    assert rm.git["branch"] in ("master", "main")
    assert any("init commit" in c for c in rm.git["recent_commits"])
