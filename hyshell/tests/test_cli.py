# Copyright (C) 2026 Tencent. Licensed under the Apache License, Version 2.0.
# SPDX-License-Identifier: Apache-2.0
"""CLI subcommands (all offline)."""

from __future__ import annotations

import pytest

from conftest import make_recorded_console

from hyshell.cli import main


def _text(console) -> str:
    return console.export_text(styles=False, clear=False)


def test_version(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    assert "hyshell 1.0.0" in capsys.readouterr().out


def test_ask_one_shot_offline(workspace, monkeypatch, tmp_path):
    monkeypatch.chdir(workspace)
    monkeypatch.setenv("HYSHELL_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("HY3_API_KEY", raising=False)
    console = make_recorded_console()
    code = main(
        ["ask", "统计一下这个项目里有多少个", "Python", "文件", "--offline", "--yes"],
        console=console,
    )
    assert code == 0
    text = _text(console)
    assert "find . -type f -name '*.py' | wc -l" in text
    assert "✓ exit 0" in text


def test_ask_dangerous_with_yes_is_refused(workspace, monkeypatch, tmp_path):
    monkeypatch.chdir(workspace)
    monkeypatch.setenv("HYSHELL_HOME", str(tmp_path / "home"))
    console = make_recorded_console()
    code = main(["ask", "把", "logs", "目录下的日志全部删掉", "--offline", "--yes"], console=console)
    assert code == 2
    assert (workspace / "logs" / "app.log").exists()


def test_demo_lists_flows():
    console = make_recorded_console()
    assert main(["demo", "--list"], console=console) == 0
    text = _text(console)
    assert "daily" in text and "guard_fix" in text


def test_demo_runs_daily_via_cli(monkeypatch, tmp_path):
    monkeypatch.delenv("HY3_API_KEY", raising=False)
    console = make_recorded_console()
    assert main(["demo", "daily"], console=console) == 0
    text = _text(console)
    assert "会话汇总" in text
    assert "OFFLINE DEMO MODE" in text


def test_demo_real_backend_requires_key(monkeypatch):
    monkeypatch.delenv("HY3_API_KEY", raising=False)
    console = make_recorded_console()
    assert main(["demo", "daily", "--backend", "real"], console=console) == 2
    assert "HY3_API_KEY" in _text(console)


def test_doctor_offline_table(monkeypatch):
    monkeypatch.delenv("HY3_API_KEY", raising=False)
    console = make_recorded_console()
    assert main(["doctor", "--offline"], console=console) == 0
    text = _text(console)
    assert "fake" in text
    assert "hy3" in text
    assert "offline" in text  # masked key placeholder


def test_doctor_ping_offline_roundtrip(monkeypatch):
    monkeypatch.delenv("HY3_API_KEY", raising=False)
    console = make_recorded_console()
    assert main(["doctor", "--offline", "--ping"], console=console) == 0
    assert "ping 成功" in _text(console)


def test_history_empty(monkeypatch, tmp_path):
    monkeypatch.setenv("HYSHELL_HOME", str(tmp_path / "empty-home"))
    monkeypatch.delenv("HY3_API_KEY", raising=False)
    console = make_recorded_console()
    assert main(["history"], console=console) == 0
    assert "暂无历史记录" in _text(console)
