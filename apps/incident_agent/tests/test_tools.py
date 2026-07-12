from __future__ import annotations

import asyncio
import subprocess
from time import monotonic

from apps.incident_agent import tools
from apps.incident_agent.tools import (
    execute_tool,
    async_run_checks,
    list_files,
    read_file,
    run_checks,
    search_files,
)


def test_list_search_and_read_are_relative(tmp_path):
    (tmp_path / "service.py").write_text(
        "alpha = 1\nneedle = alpha\n",
        encoding="utf-8",
    )

    assert "service.py" in list_files(tmp_path).content
    assert "service.py:2" in search_files(tmp_path, "needle").content
    assert "2: needle = alpha" in read_file(
        tmp_path,
        "service.py",
        2,
        2,
    ).content


def test_search_can_filter_extensions(tmp_path):
    (tmp_path / "service.py").write_text("needle\n", encoding="utf-8")
    (tmp_path / "service.log").write_text("needle\n", encoding="utf-8")

    result = search_files(tmp_path, "needle", extensions=[".log"])

    assert "service.log:1" in result.content
    assert "service.py" not in result.content


def test_path_traversal_and_unknown_tools_are_rejected(tmp_path):
    assert not read_file(tmp_path, "../secret.txt").ok
    assert not execute_tool(
        tmp_path,
        "shell",
        {"command": "rm -rf /"},
    ).ok


def test_dispatcher_validates_arguments(tmp_path):
    result = execute_tool(tmp_path, "read_file", {"path": 42})

    assert not result.ok
    assert "Invalid arguments" in result.content


def test_pytest_check_returns_bounded_failure_output(tmp_path):
    (tmp_path / "test_failure.py").write_text(
        "def test_failure():\n    assert False\n",
        encoding="utf-8",
    )

    result = run_checks(tmp_path, "pytest")

    assert not result.ok
    assert "1 failed" in result.content


def test_py_compile_and_unsupported_check(tmp_path):
    (tmp_path / "valid.py").write_text("value = 1\n", encoding="utf-8")

    assert run_checks(tmp_path, "py_compile").ok
    assert not run_checks(tmp_path, "bash").ok


def test_check_timeout_is_reported(tmp_path, monkeypatch):
    def expire(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 20)

    monkeypatch.setattr(tools.subprocess, "run", expire)

    result = run_checks(tmp_path, "pytest")

    assert not result.ok
    assert "timed out after 20 seconds" in result.content


def test_tool_output_is_truncated(tmp_path):
    (tmp_path / "large.log").write_text(
        "needle " + "x" * 13_000,
        encoding="utf-8",
    )

    result = search_files(tmp_path, "needle")

    assert len(result.content) <= 12_100
    assert result.content.endswith("...[output truncated]")


def test_workspace_tools_ignore_symlinks_to_external_files(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "valid.py").write_text("value = 1\n", encoding="utf-8")
    outside_log = tmp_path / "outside.log"
    outside_log.write_text("OUTSIDE_WORKSPACE_MARKER\n", encoding="utf-8")
    outside_python = tmp_path / "outside.py"
    outside_python.write_text("this is invalid python !!!\n", encoding="utf-8")
    (root / "linked.log").symlink_to(outside_log)
    (root / "linked.py").symlink_to(outside_python)

    assert "linked" not in list_files(root).content
    assert "OUTSIDE_WORKSPACE_MARKER" not in search_files(
        root,
        "OUTSIDE_WORKSPACE_MARKER",
    ).content
    assert run_checks(root, "py_compile").ok


def test_async_check_timeout_terminates_promptly(tmp_path):
    (tmp_path / "test_slow.py").write_text(
        "import time\n\ndef test_slow():\n    time.sleep(5)\n",
        encoding="utf-8",
    )
    started = monotonic()

    result = asyncio.run(
        async_run_checks(tmp_path, "pytest", timeout_seconds=0.1)
    )

    assert not result.ok
    assert "timed out" in result.content.lower()
    assert monotonic() - started < 2
