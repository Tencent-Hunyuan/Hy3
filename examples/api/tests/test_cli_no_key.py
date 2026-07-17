from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = [
    "01_basic_chat.py",
    "02_streaming.py",
    "03_latency_compare.py",
    "04_tool_calling.py",
    "05_reasoning_mode.py",
    "06_error_handling_retry.py",
]


@pytest.mark.parametrize("script", SCRIPTS)
def test_script_fails_safely_without_key_from_repo_root(script: str) -> None:
    env = os.environ.copy()
    env.pop("HY3_API_KEY", None)
    env["PYTHONIOENCODING"] = "utf-8"
    completed = subprocess.run(
        [sys.executable, f"examples/api/{script}"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    combined = completed.stdout + completed.stderr
    assert completed.returncode != 0
    assert "HY3_API_KEY is not set" in combined
    assert "Traceback" not in combined
