# Copyright (C) 2026 Tencent. Licensed under the Apache License, Version 2.0.
# SPDX-License-Identifier: Apache-2.0
"""Executor: capture, exit codes, timeout kill, cwd, truncation."""

from __future__ import annotations

import time
from pathlib import Path

from hyshell.executor import TIMEOUT_EXIT_CODE, run_command


def _pipeline_survivors(marker: str) -> list[str]:
    """PIDs of still-running processes whose command line carries ``marker``."""
    survivors = []
    for proc_dir in Path("/proc").iterdir():
        if not proc_dir.name.isdigit():
            continue
        try:
            cmdline = (proc_dir / "cmdline").read_bytes().replace(b"\0", b" ").decode()
        except OSError:
            continue  # process exited while scanning
        if marker in cmdline and "bash" not in cmdline:
            survivors.append(proc_dir.name)
    return survivors


def test_stdout_exit_captured(tmp_path):
    result = run_command("echo hello", cwd=tmp_path)
    assert result.exit_code == 0
    assert result.stdout.strip() == "hello"
    assert result.stderr == ""
    assert result.ok


def test_stderr_on_failure(tmp_path):
    result = run_command("echo boom >&2; exit 3", cwd=tmp_path)
    assert result.exit_code == 3
    assert "boom" in result.stderr
    assert not result.ok


def test_timeout_sets_flag_and_kills(tmp_path):
    started = time.monotonic()
    result = run_command("sleep 5", cwd=tmp_path, timeout=0.5)
    elapsed = time.monotonic() - started
    assert result.timed_out
    assert result.exit_code == TIMEOUT_EXIT_CODE
    assert not result.ok
    assert elapsed < 3.0


def test_timeout_kills_whole_pipeline_group(tmp_path):
    # A unique duration marks our processes; the group kill must reap the
    # pipeline children too, not just the bash parent.
    marker = "61.73"
    result = run_command(f"sleep {marker} | sleep {marker}", cwd=tmp_path, timeout=0.5)
    assert result.timed_out
    assert result.exit_code == TIMEOUT_EXIT_CODE
    time.sleep(0.2)  # give the kernel a beat to reap
    assert _pipeline_survivors(marker) == []


def test_cwd_respected(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "marker.txt").write_text("x", encoding="utf-8")
    result = run_command("ls", cwd=sub)
    assert "marker.txt" in result.stdout


def test_non_utf8_output_replaced_never_raises(tmp_path):
    # \xff\xfe is invalid UTF-8 — must decode via replacement chars, not crash
    result = run_command("printf '\\xff\\xfe bin'; printf 'err \\xff' >&2", cwd=tmp_path)
    assert result.exit_code == 0
    assert "�" in result.stdout
    assert "�" in result.stderr


def test_output_truncated(tmp_path):
    result = run_command("printf 'x%.0s' $(seq 1 10000)", cwd=tmp_path)
    assert result.exit_code == 0
    assert len(result.stdout) < 4200
    assert "截断" in result.stdout
