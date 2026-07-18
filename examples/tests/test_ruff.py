"""Ensure examples stay ruff-clean (format + lint)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("ruff") is None, reason="ruff not installed")
def test_ruff_format_check():
    proc = subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--check", str(ROOT)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


@pytest.mark.skipif(shutil.which("ruff") is None, reason="ruff not installed")
def test_ruff_check():
    proc = subprocess.run(
        [sys.executable, "-m", "ruff", "check", str(ROOT)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
