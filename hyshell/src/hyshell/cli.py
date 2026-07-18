# Copyright (C) 2026 Tencent. Licensed under the Apache License, Version 2.0.
# SPDX-License-Identifier: Apache-2.0
"""hyshell command-line entry point.

Subcommands::

    hyshell                          # interactive REPL (default)
    hyshell ask "把日志都删了" [--yes]  # one-shot request
    hyshell demo daily|guard_fix     # scripted offline demo (--backend real to replay)
    hyshell history [--last N]
    hyshell doctor [--ping]          # environment check (mode/endpoint/model/key)

Common flags: ``--offline`` (force fake backend), ``--yes`` (auto-confirm;
dangerous commands are still refused), ``--version``.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from hyshell import __version__
from hyshell.config import BackendMode, Settings
from hyshell.history import HistoryStore
from hyshell.tui import InteractiveInput, Tui


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    # SUPPRESS keeps subcommand defaults from clobbering root-level flags.
    common.add_argument(
        "--offline",
        action="store_true",
        default=argparse.SUPPRESS,
        help="强制离线模式(内置确定性伪 Hy3 后端)",
    )
    common.add_argument(
        "--yes",
        action="store_true",
        default=argparse.SUPPRESS,
        help="自动确认 safe/caution 命令(dangerous 仍会被拒绝)",
    )

    parser = argparse.ArgumentParser(
        prog="hyshell",
        description="hyshell — Hy3 驱动的终端命令行助手(说人话,出命令;先审危险,再敲回车)",
        parents=[common],
    )
    parser.set_defaults(offline=False, yes=False, cmd=None)
    parser.add_argument("--version", action="version", version=f"hyshell {__version__}")
    sub = parser.add_subparsers(dest="cmd")

    ask = sub.add_parser("ask", parents=[common], help="单发请求:自然语言 → 命令 → 确认 → 执行")
    ask.add_argument("request", nargs="+", help="自然语言请求(可不加引号)")

    demo = sub.add_parser("demo", parents=[common], help="运行脚本化端到端演示流程")
    demo.add_argument("flow", nargs="?", default=None, help="流程名(daily / guard_fix)")
    demo.add_argument("--backend", choices=["fake", "real"], default="fake",
                      help="fake=离线确定性伪后端(默认); real=真实 Hy3(需 HY3_API_KEY)")
    demo.add_argument("--list", action="store_true", help="列出可用流程")
    demo.add_argument("--keep-workspace", action="store_true", help="保留演示工作目录")

    history = sub.add_parser("history", parents=[common], help="查看最近会话历史")
    history.add_argument("--last", type=int, default=10, metavar="N", help="显示最近 N 条(默认 10)")

    doctor = sub.add_parser("doctor", parents=[common], help="环境体检:后端模式/端点/模型/密钥")
    doctor.add_argument("--ping", action="store_true", help="向后端发送一条最小请求验证连通性")
    return parser


def main(argv: list[str] | None = None, console: Console | None = None) -> int:
    args = build_parser().parse_args(argv)
    console = console or Console()
    offline = getattr(args, "offline", False)
    auto_yes = getattr(args, "yes", False)
    command = args.cmd or "repl"
    if command == "repl":
        return _cmd_repl(console, offline, auto_yes)
    if command == "ask":
        return _cmd_ask(args, console, offline, auto_yes)
    if command == "demo":
        return _cmd_demo(args, console)
    if command == "history":
        return _cmd_history(args, console, offline)
    if command == "doctor":
        return _cmd_doctor(args, console, offline)
    raise AssertionError(f"unhandled command {command!r}")  # pragma: no cover


# ---------------------------------------------------------------------------


def _cmd_repl(console: Console, offline: bool, auto_yes: bool) -> int:
    from hyshell.app import ShellAssistantApp

    settings = Settings.from_env(offline=offline, auto_yes=auto_yes)
    app = ShellAssistantApp(
        settings=settings,
        console=console,
        input_source=InteractiveInput(console),
        workdir=Path.cwd(),
    )
    app.run_repl()
    return 0


def _cmd_ask(args: argparse.Namespace, console: Console, offline: bool, auto_yes: bool) -> int:
    from hyshell.app import ShellAssistantApp

    settings = Settings.from_env(offline=offline, auto_yes=auto_yes)
    app = ShellAssistantApp(
        settings=settings,
        console=console,
        input_source=InteractiveInput(console),
        workdir=Path.cwd(),
    )
    Tui(console).banner(settings)
    record = app.run_turn(" ".join(args.request))
    if record.blocked:
        return 2
    if record.executed and record.exit_code != 0:
        return 1
    return 0


def _cmd_demo(args: argparse.Namespace, console: Console) -> int:
    from hyshell.demo_flows import FLOWS, run_flow

    tui = Tui(console)
    if args.list or not args.flow:
        table = Table(title="可用演示流程 Demo Flows", box=box.SIMPLE_HEAVY)
        table.add_column("名称", style="bold")
        table.add_column("标题")
        table.add_column("内容")
        for flow in FLOWS.values():
            table.add_row(flow.name, flow.title_zh, flow.description_zh)
        console.print(table)
        return 0
    if args.flow not in FLOWS:
        tui.error(f"未知流程: {args.flow}(可用: {', '.join(FLOWS)})")
        return 2

    if args.backend == "real":
        settings = Settings.from_env()
        if settings.mode is BackendMode.FAKE:
            tui.error("--backend real 需要设置 HY3_API_KEY(参见 README 配置章节)。")
            return 2
    else:
        settings = Settings.from_env({}, offline=True)

    tmp_root = Path(tempfile.mkdtemp(prefix="hyshell-demo-"))
    workdir = tmp_root / "workspace"
    settings = replace(settings, home_dir=tmp_root / "home")
    try:
        run_flow(args.flow, console=console, workdir=workdir, settings=settings)
    finally:
        if args.keep_workspace:
            console.print(Text(f"演示工作目录已保留: {workdir}", style="dim"))
        else:
            shutil.rmtree(tmp_root, ignore_errors=True)
    return 0


def _cmd_history(args: argparse.Namespace, console: Console, offline: bool) -> int:
    settings = Settings.from_env(offline=offline)
    entries = HistoryStore(settings.home_dir).load_last(args.last)
    tui = Tui(console)
    if not entries:
        tui.info("暂无历史记录。")
        return 0
    tui.show_history(entries)
    return 0


def _cmd_doctor(args: argparse.Namespace, console: Console, offline: bool) -> int:
    settings = Settings.from_env(offline=offline)
    table = Table(title="hyshell doctor — 环境体检", box=box.SIMPLE_HEAVY)
    table.add_column("项目", style="bold")
    table.add_column("值")
    table.add_row("后端模式 backend", settings.mode.value)
    table.add_row(
        "API base",
        "(in-process fake)" if settings.mode is BackendMode.FAKE else settings.api_base,
    )
    table.add_row("模型 model", settings.model)
    table.add_row("API key", settings.masked_key())
    table.add_row("temperature / top_p", f"{settings.temperature} / {settings.top_p}")
    table.add_row("reasoning_effort", settings.reasoning_effort or "(未设置,不传该参数)")
    table.add_row("请求超时 timeout", f"{settings.request_timeout}s")
    table.add_row("历史目录 home", str(settings.home_dir))
    table.add_row("版本 version", __version__)
    console.print(table)
    tui = Tui(console)
    if settings.mode is BackendMode.FAKE:
        tui.info("离线模式:零配置可用;设置 HY3_API_KEY 后自动切换真实后端。")
    if args.ping:
        from hyshell.llm import Hy3Client

        try:
            reply = Hy3Client(settings).ping()
        except Exception as exc:  # noqa: BLE001 - doctor reports any failure
            tui.error(f"ping 失败: {exc}")
            return 1
        tui.success(f"ping 成功,后端应答: {reply[:60]}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
