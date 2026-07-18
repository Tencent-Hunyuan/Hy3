# Copyright (C) 2026 Tencent. Licensed under the Apache License, Version 2.0.
# SPDX-License-Identifier: Apache-2.0
"""Scripted end-to-end demo flows (deterministic, offline by default).

The same flows are consumed three ways:

* the e2e test suite runs them in-process and asserts on the transcripts;
* ``demo/record_gifs.py`` runs them to produce the two shipped GIFs;
* ``hyshell demo <flow> --backend real`` replays them against a real
  ``HY3_API_KEY`` (real model output is non-deterministic — the scripted
  inputs may diverge, which ends the demo early and is expected).

The demo workspace content is fixed byte-for-byte so command output is
deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

from rich.console import Console

from hyshell.app import ShellAssistantApp
from hyshell.config import Settings
from hyshell.tui import ScriptedInput, ScriptExhausted, Tui


@dataclass(frozen=True)
class DemoFlow:
    """A named, fully scripted REPL session."""

    name: str
    title_zh: str
    description_zh: str
    inputs: tuple[str, ...]


FLOWS: dict[str, DemoFlow] = {
    "daily": DemoFlow(
        name="daily",
        title_zh="日常流程:自然语言 → 命令 → 确认 → 执行",
        description_zh="两条只读请求:统计 Python 文件数量、找出最大的 3 个文件。",
        inputs=(
            "统计一下这个项目里有多少个 Python 文件",
            "",  # safe gate → Enter
            "找出占用空间最大的 3 个文件",
            "",  # safe gate → Enter
            "exit",
        ),
    ),
    "guard_fix": DemoFlow(
        name="guard_fix",
        title_zh="安全拦截 + 错误自愈流程",
        description_zh=(
            "rm -rf 被双层安全引擎拦截 → Hy3 给安全替代;"
            "head 不存在的文件失败 → Hy3 诊断修复 → 重试成功。"
        ),
        inputs=(
            "把 logs 目录下的日志全部删掉",
            "a",   # dangerous gate → ask Hy3 for a safer alternative
            "y",   # alternative is caution → confirm
            "看看 report.txt 的前 5 行",
            "",    # safe gate → Enter (fails: no report.txt)
            "",    # fix suggestion (head report.md, safe) → Enter
            "exit",
        ),
    ),
}


def setup_workspace(root: Path) -> None:
    """Create the fixed demo workspace (all content byte-deterministic)."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "logs").mkdir(exist_ok=True)
    (root / "src").mkdir(exist_ok=True)
    (root / "big").mkdir(exist_ok=True)
    (root / "logs" / "app.log").write_text(
        "2026-07-01 INFO service started\n"
        "2026-07-01 INFO healthcheck ok\n"
        "2026-07-02 WARN slow response 1200ms\n",
        encoding="utf-8",
    )
    (root / "logs" / "debug.log").write_text(
        "2026-07-02 DEBUG cache miss key=user:42\n"
        "2026-07-02 DEBUG retry backoff 200ms\n",
        encoding="utf-8",
    )
    (root / "report.md").write_text(
        "# 本周工作周报\n"
        "\n"
        "- 完成 hyshell 安全引擎联调\n"
        "- 修复日志轮转脚本的越界问题\n"
        "- 下周计划:接入 Hy3 修复循环\n",
        encoding="utf-8",
    )
    (root / "data.csv").write_text(
        "date,requests,errors\n"
        "2026-07-01,1032,3\n"
        "2026-07-02,1187,1\n"
        "2026-07-03,996,0\n"
        "2026-07-04,1210,2\n",
        encoding="utf-8",
    )
    (root / "src" / "main.py").write_text(
        "def main() -> None:\n"
        "    print('hello hyshell')\n"
        "\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    main()\n",
        encoding="utf-8",
    )
    (root / "src" / "util.py").write_text(
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n",
        encoding="utf-8",
    )
    (root / "big" / "archive.bin").write_bytes(b"\0" * (150 * 1024))


def run_flow(
    name: str,
    *,
    console: Console,
    workdir: Path,
    settings: Settings | None = None,
    frame_hook: Callable[[], None] | None = None,
) -> ShellAssistantApp:
    """Run one scripted flow end-to-end; returns the app (for its records)."""
    flow = FLOWS[name]
    if settings is None:
        settings = replace(
            Settings.from_env({}, offline=True),
            home_dir=workdir.parent / "hyshell-home",
        )
    setup_workspace(workdir)
    scripted = ScriptedInput(list(flow.inputs), console=console, on_ask=frame_hook)
    app = ShellAssistantApp(
        settings=settings,
        console=console,
        input_source=scripted,
        workdir=workdir,
    )
    try:
        app.run_repl()
    except ScriptExhausted:
        # Expected with --backend real: non-deterministic model output makes
        # the scripted inputs diverge. Never happens in offline mode (tested).
        Tui(console).warn("脚本输入与模型输出分叉,演示提前结束(真实后端下属预期现象)。")
    if frame_hook is not None:
        frame_hook()
    return app
