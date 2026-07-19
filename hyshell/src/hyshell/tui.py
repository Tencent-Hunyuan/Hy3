# Copyright (C) 2026 Tencent. Licensed under the Apache License, Version 2.0.
# SPDX-License-Identifier: Apache-2.0
"""rich-based terminal UI + input abstraction.

Determinism contract (relied on by the e2e tests and the GIF pipeline): the
TUI never prints timestamps, durations or absolute paths — the transcript of
a scripted demo flow is byte-for-byte reproducible.  Only static rich
renderables are used (Panel/Table/Text), which export as a pure SGR ANSI
stream (verified on rich 15).
"""

from __future__ import annotations

from collections import deque
from typing import Callable, Iterable, Protocol, Sequence

from rich import box
from rich.console import Console
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from hyshell import SLOGAN_ZH, __version__
from hyshell.config import BackendMode, Settings
from hyshell.schema import (
    CommandPlan,
    ExecutionResult,
    FixSuggestion,
    RiskLevel,
    TurnRecord,
)

OFFLINE_BANNER = "OFFLINE DEMO MODE (fake Hy3 backend) — 离线演示:内置确定性伪 Hy3 后端"

_SOURCE_LABELS = {
    "plan": "Hy3 方案",
    "alt": "Hy3 安全替代",
    "edit": "用户编辑",
    "fix": "Hy3 修复命令",
}

_RISK_BORDER = {
    RiskLevel.SAFE: "green",
    RiskLevel.CAUTION: "yellow",
    RiskLevel.DANGEROUS: "red",
}

_CONFIDENCE_STYLE = {"high": "bold green", "medium": "bold yellow", "low": "bold red"}


class ScriptExhausted(RuntimeError):
    """A scripted demo ran out of predefined inputs (never swallowed silently)."""


class InputSource(Protocol):
    """Anything that can answer a prompt (interactive terminal or a script)."""

    def ask(self, prompt: str, *, default: str | None = None) -> str:  # pragma: no cover
        ...


class InteractiveInput:
    """Reads real user input from the console."""

    def __init__(self, console: Console) -> None:
        self._console = console

    def ask(self, prompt: str, *, default: str | None = None) -> str:
        try:
            return self._console.input(prompt)
        except (EOFError, KeyboardInterrupt):
            self._console.print()
            return "exit"


class ScriptedInput:
    """Feeds a fixed input sequence and echoes it into the console.

    * echoing makes typed answers visible in transcripts and GIF frames;
    * an optional ``on_ask`` hook fires after the prompt is printed but
      before the answer — the GIF recorder uses it to capture "waiting for
      input" frames;
    * running out of inputs raises :class:`ScriptExhausted` so a demo can
      never silently skip steps.
    """

    def __init__(
        self,
        inputs: Sequence[str],
        *,
        console: Console,
        on_ask: Callable[[], None] | None = None,
    ) -> None:
        self._queue: deque[str] = deque(inputs)
        self._console = console
        self._on_ask = on_ask

    @property
    def remaining(self) -> int:
        return len(self._queue)

    def ask(self, prompt: str, *, default: str | None = None) -> str:
        self._console.print(Text.from_markup(prompt), end="")
        if self._on_ask is not None:
            self._on_ask()
        if not self._queue:
            self._console.print()
            raise ScriptExhausted(f"脚本输入序列已耗尽,仍在等待输入: {prompt!r}")
        value = self._queue.popleft()
        display = value if value != "" else "⏎"
        self._console.print(Text(display, style="bold bright_cyan"))
        return value


class Tui:
    """All rendering goes through here (accepts an injected/record console)."""

    def __init__(self, console: Console) -> None:
        self.console = console

    # -- blocks --------------------------------------------------------------

    def banner(self, settings: Settings) -> None:
        body = Text()
        body.append(f"hyshell v{__version__}", style="bold bright_blue")
        body.append(f" — {SLOGAN_ZH}\n", style="bold")
        body.append("Hy3 角色: 命令规划 · 危险解释 · 安全替代 · 错误诊断修复\n", style="dim")
        body.append(
            "(全部经 OpenAI 兼容 chat.completions API,无训练/微调/本地推理)\n",
            style="dim",
        )
        if settings.mode is BackendMode.FAKE:
            body.append("⚠ " + OFFLINE_BANNER + "\n", style="bold yellow")
            body.append(f"backend: in-process fake · model: {settings.model}", style="dim")
        else:
            body.append(f"backend: {settings.api_base} · model: {settings.model}", style="dim")
        self.console.print(Panel(body, border_style="bright_blue", box=box.ROUNDED))

    def show_plan(
        self,
        plan: CommandPlan,
        final: RiskLevel,
        reasons: Iterable[str],
        *,
        source: str = "plan",
    ) -> None:
        body = Text()
        body.append("$ ", style="bold green")
        body.append(plan.command, style="bold white")
        body.append("\n说明: ", style="bold")
        body.append(plan.explanation)
        if plan.notes:
            body.append("\n备注: ", style="dim bold")
            body.append(plan.notes, style="dim")
        reason_list = list(reasons)
        if reason_list:
            body.append("\n风险理由:", style="bold")
            for reason in reason_list:
                style = "yellow" if final is RiskLevel.CAUTION else "red"
                if final is RiskLevel.SAFE:
                    style = "dim"
                body.append(f"\n  • {reason}", style=style)
        title = Text(f"{_SOURCE_LABELS.get(source, source)} · 风险: ")
        title.append(f" {final.label_zh} {final.label_en} ", style=final.badge_style)
        self.console.print(
            Panel(body, title=title, title_align="left", border_style=_RISK_BORDER[final], box=box.ROUNDED)
        )

    def show_execution(self, result: ExecutionResult) -> None:
        if result.ok:
            self.console.print(Text(f"✓ exit {result.exit_code}", style="bold green"))
        else:
            suffix = " (超时 timeout)" if result.timed_out else ""
            self.console.print(Text(f"✗ exit {result.exit_code}{suffix}", style="bold red"))
        stdout = result.stdout.rstrip()
        stderr = result.stderr.rstrip()
        if stdout:
            self.console.print(Padding(Text(stdout), (0, 0, 0, 2)))
        elif result.ok and not stderr:
            self.console.print(Text("  (无输出)", style="dim"))
        if stderr:
            self.console.print(Padding(Text(stderr, style="red"), (0, 0, 0, 2)))

    def show_fix(self, suggestion: FixSuggestion) -> None:
        line = Text("Hy3 诊断: ", style="bold cyan")
        line.append(suggestion.diagnosis)
        line.append("  [置信度 ", style="dim")
        line.append(suggestion.confidence, style=_CONFIDENCE_STYLE[suggestion.confidence])
        line.append("]", style="dim")
        self.console.print(line)

    def show_summary(self, records: Sequence[TurnRecord]) -> None:
        table = Table(title="会话汇总 Session Summary", box=box.SIMPLE_HEAVY)
        table.add_column("#", justify="right", style="dim")
        table.add_column("请求", max_width=16, no_wrap=True)
        table.add_column("命令", max_width=26, no_wrap=True)
        table.add_column("风险", no_wrap=True)
        table.add_column("结果", no_wrap=True)
        for index, record in enumerate(records, 1):
            risk = record.risk_final.label_zh if record.risk_final is not None else "-"
            table.add_row(
                str(index),
                _shorten(record.request, 16),
                _shorten(record.command or "-", 26),
                risk,
                _outcome_text(record),
            )
        self.console.print(table)
        executed_ok = sum(1 for r in records if r.executed and r.exit_code == 0)
        blocked = sum(1 for r in records if r.blocked)
        alts = sum(1 for r in records if r.source == "alt")
        fixes = sum(1 for r in records if r.source == "fix" and r.executed and r.exit_code == 0)
        self.console.print(
            Text(
                f"共 {len(records)} 轮 · 执行成功 {executed_ok} · 已拦截 {blocked}"
                f" · 安全替代 {alts} · 修复成功 {fixes}",
                style="bold",
            )
        )

    def show_history(self, entries: Sequence[dict]) -> None:
        table = Table(title="最近历史 Recent History", box=box.SIMPLE_HEAVY)
        table.add_column("时间", style="dim", no_wrap=True)
        table.add_column("请求", max_width=18, no_wrap=True)
        table.add_column("命令", max_width=24, no_wrap=True)
        table.add_column("exit", justify="right")
        for entry in entries:
            table.add_row(
                str(entry.get("ts", "-")),
                _shorten(str(entry.get("request", "-")), 18),
                _shorten(str(entry.get("command") or "-"), 24),
                str(entry.get("exit_code", "-")),
            )
        self.console.print(table)

    # -- one-liners -----------------------------------------------------------

    def info(self, message: str) -> None:
        self.console.print(Text("→ " + message, style="cyan"))

    def warn(self, message: str) -> None:
        self.console.print(Text("⚠ " + message, style="yellow"))

    def error(self, message: str) -> None:
        self.console.print(Text("✗ " + message, style="bold red"))

    def success(self, message: str) -> None:
        self.console.print(Text("✔ " + message, style="bold green"))


def _shorten(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _outcome_text(record: TurnRecord) -> Text:
    if record.blocked:
        return Text("✗ 已拦截", style="bold red")
    if not record.executed:
        return Text("→ 跳过", style="dim")
    if record.exit_code == 0:
        label = "✓ 成功"
        if record.fix_attempts and record.source == "fix":
            label += f"(修复×{record.fix_attempts})"
        return Text(label, style="green")
    return Text(f"✗ exit {record.exit_code}", style="red")
