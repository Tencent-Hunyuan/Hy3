# Copyright (C) 2026 Tencent. Licensed under the Apache License, Version 2.0.
# SPDX-License-Identifier: Apache-2.0
"""End-to-end demo flows in-process: transcripts, determinism, gate invariants."""

from __future__ import annotations

from pathlib import Path

from conftest import SpyRunner, make_recorded_console

from hyshell.demo_flows import run_flow
from hyshell.tui import OFFLINE_BANNER


def _run(name: str, tmp_path: Path, sub: str = "run"):
    console = make_recorded_console()
    app = run_flow(name, console=console, workdir=tmp_path / sub / "workspace")
    plain = console.export_text(styles=False, clear=False)
    styled = console.export_text(styles=True, clear=False)
    return app, plain, styled


def test_demo_daily_flow_end_to_end(tmp_path):
    app, plain, _ = _run("daily", tmp_path)
    assert OFFLINE_BANNER in plain
    assert "find . -type f -name '*.py' | wc -l" in plain
    assert "sort -rn | head -n 3" in plain
    assert "archive.bin" in plain  # largest file listed
    assert "✓ exit 0" in plain
    assert "会话汇总" in plain
    assert "执行成功 2" in plain
    records = app.records
    assert len(records) == 2
    assert all(r.executed and r.exit_code == 0 for r in records)
    assert all(r.source == "plan" for r in records)
    assert records[0].mode == "fake"


def test_demo_guard_fix_flow_end_to_end(tmp_path):
    app, plain, _ = _run("guard_fix", tmp_path)
    # ① dangerous plan intercepted, safer alternative executed
    assert "rm -rf logs/*.log" in plain
    assert "危险 DANGEROUS" in plain
    assert "[本地规则 rm-recursive-force]" in plain
    assert "find logs -name '*.log' -mtime +30 -print" in plain
    # ② failure → Hy3 diagnosis → fixed command succeeds
    assert "head -n 5 report.txt" in plain
    assert "No such file" in plain
    assert "head -n 5 report.md" in plain
    assert "修复成功(第 1 次重试)" in plain
    assert "本周工作周报" in plain
    assert "安全替代 1" in plain and "修复成功 1" in plain
    records = app.records
    assert len(records) == 2
    assert records[0].source == "alt" and records[0].exit_code == 0
    assert records[1].source == "fix" and records[1].fix_attempts == 1 and records[1].exit_code == 0
    # the dangerous rm never ran: log files are intact
    workspace = tmp_path / "run" / "workspace"
    assert (workspace / "logs" / "app.log").exists()
    assert (workspace / "logs" / "debug.log").exists()


def test_transcripts_deterministic_across_runs(tmp_path):
    for flow in ("daily", "guard_fix"):
        _, _, styled_a = _run(flow, tmp_path, sub=f"{flow}-a")
        _, _, styled_b = _run(flow, tmp_path, sub=f"{flow}-b")
        assert styled_a == styled_b, f"flow {flow} transcript not byte-deterministic"


def test_dangerous_never_runs_without_typed_RUN(make_app, workspace):
    spy = SpyRunner()
    dangerous_request = "把 logs 目录下的日志全部删掉"
    for wrong_answer in ("y", "yes", "", "run"):  # even lowercase "run" must fail
        app, console = make_app([wrong_answer], workdir=workspace, runner=spy)
        record = app.run_turn(dangerous_request)
        assert record.blocked, f"answer {wrong_answer!r} must block"
        assert not record.executed
        assert "已拒绝执行" in console.export_text(styles=False, clear=False)
    assert spy.commands == []
    assert (workspace / "logs" / "app.log").exists()


def test_dangerous_skip_is_not_blocked(make_app, workspace):
    spy = SpyRunner()
    app, _ = make_app(["s"], workdir=workspace, runner=spy)
    record = app.run_turn("把 logs 目录下的日志全部删掉")
    assert not record.blocked and not record.executed
    assert spy.commands == []


def test_yes_mode_still_refuses_dangerous(make_app, workspace):
    spy = SpyRunner()
    app, console = make_app([], workdir=workspace, auto_yes=True, runner=spy)
    record = app.run_turn("把 logs 目录下的日志全部删掉")
    assert record.blocked
    assert spy.commands == []
    assert "--yes 模式仍然拒绝执行 dangerous 命令" in console.export_text(
        styles=False, clear=False
    )


def test_yes_mode_runs_safe_without_input(make_app, workspace):
    app, _ = make_app([], workdir=workspace, auto_yes=True)
    record = app.run_turn("统计一下这个项目里有多少个 Python 文件")
    assert record.executed and record.exit_code == 0


def test_edit_path_reassesses_locally(make_app, workspace):
    spy = SpyRunner()
    app, console = make_app(["e", "echo edited", ""], workdir=workspace, runner=spy)
    record = app.run_turn("统计一下这个项目里有多少个 Python 文件")
    assert record.source == "edit"
    assert record.command == "echo edited"
    assert spy.commands == ["echo edited"]
    assert "用户编辑" in console.export_text(styles=False, clear=False)


def test_edited_dangerous_command_still_gated(make_app, workspace):
    spy = SpyRunner()
    # edit a safe plan into a dangerous command → gate must demand RUN
    app, _ = make_app(["e", "rm -rf logs", "y"], workdir=workspace, runner=spy)
    record = app.run_turn("统计一下这个项目里有多少个 Python 文件")
    assert record.blocked
    assert spy.commands == []


def test_runner_error_becomes_failed_result_not_crash(make_app, workspace):
    # A runner-level OSError (spawn failure, …) must NOT crash the REPL turn:
    # it becomes a normal failed result — rendered, fix-looped and recorded.
    def exploding_runner(command, *, cwd, timeout: float = 30.0):
        raise OSError("no pty available")

    app, console = make_app([], workdir=workspace, auto_yes=True, runner=exploding_runner)
    record = app.run_turn("统计一下这个项目里有多少个 Python 文件")
    assert record.executed
    assert record.exit_code != 0
    plain = console.export_text(styles=False, clear=False)
    assert "no pty available" in plain
    assert "执行器异常" in plain


def test_caution_defaults_to_no(make_app, workspace):
    spy = SpyRunner()
    app, _ = make_app([""], workdir=workspace, runner=spy)
    record = app.run_turn("帮我安装 htop")
    assert not record.executed
    assert spy.commands == []


def test_history_persisted_for_flow(tmp_path):
    app, _, _ = _run("daily", tmp_path)
    entries = app.history.load_last(10)
    assert len(entries) == 2
    assert entries[0]["command"] == "find . -type f -name '*.py' | wc -l"
    assert entries[0]["mode"] == "fake"
