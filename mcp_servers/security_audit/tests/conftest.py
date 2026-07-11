"""Shared pytest fixtures: real throwaway git repos for git_utils/server tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def run_git(args: list[str], cwd: Path) -> None:
    """Run a git command in `cwd`, raising if it fails (test setup, not SUT)."""
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """A freshly `git init`-ed repo in tmp_path, configured for local commits.

    `commit.gpgsign=false` is set locally on this throwaway repo only (never
    touches the user's global git config) so commits succeed even when the
    user's global config has commit signing turned on.
    """
    run_git(["init"], tmp_path)
    run_git(["config", "user.email", "test@example.com"], tmp_path)
    run_git(["config", "user.name", "Test"], tmp_path)
    run_git(["config", "commit.gpgsign", "false"], tmp_path)
    return tmp_path
