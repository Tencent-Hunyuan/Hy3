# Copyright (C) 2026 Tencent. Licensed under the Apache License, Version 2.0.
# SPDX-License-Identifier: Apache-2.0
"""Fix loop: success, retry exhaustion, user skip, dangerous fix still gated."""

from __future__ import annotations


def _transcript(console) -> str:
    return console.export_text(styles=False, clear=False)


def test_fix_then_success(make_app, workspace, spy_runner):
    app, console = make_app(["", ""], workdir=workspace, runner=spy_runner)
    record = app.run_turn("看看 report.txt 的前 5 行")
    assert record.fix_attempts == 1
    assert record.source == "fix"
    assert record.command == "head -n 5 report.md"
    assert record.exit_code == 0
    assert spy_runner.commands == ["head -n 5 report.txt", "head -n 5 report.md"]
    text = _transcript(console)
    assert "修复成功(第 1 次重试)" in text
    assert "本周工作周报" in text


def test_max_retries_exhausted(make_app, workspace, spy_runner):
    # data2.csv missing → fix suggests data_backup.csv (also missing) → retry x2
    app, console = make_app(["", "", ""], workdir=workspace, runner=spy_runner)
    record = app.run_turn("看一下 data2.csv 的内容")
    assert record.fix_attempts == app.settings.max_fix_retries == 2
    assert record.exit_code != 0
    assert record.source == "plan"  # never successfully fixed
    assert spy_runner.commands == [
        "cat data2.csv",
        "cat data_backup.csv",
        "cat data_backup.csv",
    ]
    assert "已达最大修复重试次数" in _transcript(console)


def test_user_skip_stops(make_app, workspace, spy_runner):
    app, console = make_app(["", "s"], workdir=workspace, runner=spy_runner)
    record = app.run_turn("看看 report.txt 的前 5 行")
    assert record.fix_attempts == 1
    assert record.exit_code == 1  # original failure kept
    assert spy_runner.commands == ["head -n 5 report.txt"]  # fix never executed
    assert "已跳过修复命令" in _transcript(console)


def test_dangerous_fix_still_gated(make_app, workspace, spy_runner):
    # cat locked.txt fails → fake suggests "sudo rm -rf locked_dir" (locally DANGEROUS)
    # user answers "y" (not RUN) → refused, nothing executed
    app, console = make_app(["", "y"], workdir=workspace, runner=spy_runner)
    record = app.run_turn("读取 locked.txt 文件")
    assert record.fix_attempts == 1
    assert record.exit_code == 1
    assert spy_runner.commands == ["cat locked.txt"]
    assert all("rm -rf" not in c for c in spy_runner.commands)
    text = _transcript(console)
    assert "已拒绝执行" in text
    assert "[本地规则" in text
