"""Ingestion — merge agent transcripts (N1) with git as the first source of truth.

Git facts are the reliable core: even if an agent log format changes, the diff /
commit history still tells us what actually changed. Agent transcripts are an
enhancement layered on top (DESIGN.md §3.3).

The git runner is injectable so tests don't need a real repo.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ctxpilot.models import SessionTranscript

GitRunner = Callable[[list[str]], "subprocess.CompletedProcess[str]"]


@dataclass
class RawMaterial:
    project_path: str
    git: dict = field(default_factory=dict)
    transcripts: list[SessionTranscript] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "project_path": self.project_path,
            "git": self.git,
            "transcripts": [t.to_dict() for t in self.transcripts],
        }


def _default_runner(args: list[str], cwd) -> "subprocess.CompletedProcess[str]":
    try:
        return subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True, text=True, check=False
        )
    except OSError:
        # cwd missing / git not on PATH — degrade gracefully (no git facts)
        return subprocess.CompletedProcess(args, returncode=1, stdout="", stderr="")


def git_collect(project_path: str | Path, runner: GitRunner | None = None) -> dict:
    run = runner or (lambda a: _default_runner(a, project_path))

    def safe(args: list[str], default: str = "") -> str:
        r = run(args)
        return r.stdout.strip() if r.returncode == 0 else default

    branch = safe(["rev-parse", "--abbrev-ref", "HEAD"], default="(detached)")
    log_raw = safe(["log", "--oneline", "-10"])
    status_raw = safe(["status", "--porcelain"])
    diff_stat = safe(["diff", "--stat", "HEAD"])
    return {
        "branch": branch,
        "recent_commits": [l for l in log_raw.splitlines() if l],
        "status": [l for l in status_raw.splitlines() if l],
        "diff_stat": diff_stat,
    }


def collect(
    project_path: str | Path,
    adapters: list | None = None,
    run_git: bool = True,
    git_runner: GitRunner | None = None,
) -> RawMaterial:
    if adapters is None:
        from ctxpilot.adapters.base import discover_adapters, get_adapter, list_adapters

        discover_adapters()
        adapters = [get_adapter(n) for n in list_adapters()]

    transcripts: list[SessionTranscript] = []
    for ad in adapters:
        try:
            sessions = ad.discover_sessions()
        except Exception:
            continue
        for s in sessions:
            try:
                transcripts.append(ad.parse_session(s))
            except Exception:
                # tolerant: one bad session must not break the whole run
                continue

    git = git_collect(project_path, runner=git_runner) if run_git else {}
    return RawMaterial(project_path=str(project_path), git=git, transcripts=transcripts)
