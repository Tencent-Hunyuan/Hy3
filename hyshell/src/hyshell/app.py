# Copyright (C) 2026 Tencent. Licensed under the Apache License, Version 2.0.
# SPDX-License-Identifier: Apache-2.0
"""The hyshell application state machine.

Per turn: ``REQUEST → PLAN (Hy3) → ASSESS (model ∨ local rules) → GATE
(confirm) → EXECUTE → (on failure: FIXLOOP → GATE → EXECUTE …) → RECORD``.

Confirmation gate by final risk level:

===========  =========================================  =======================
final risk   interactive                                ``--yes`` (non-interactive)
===========  =========================================  =======================
safe         Enter=run · e=edit · s=skip                run
caution      y/N (default N) · e=edit · s=skip          run + warning
dangerous    must type ``RUN`` · a=Hy3 alternative ·    **refused**
             s=skip
===========  =========================================  =======================
"""

from __future__ import annotations

import subprocess
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable

from openai import OpenAIError
from rich.console import Console

from hyshell.config import Settings
from hyshell.executor import EXEC_ERROR_EXIT_CODE, run_command
from hyshell.fixloop import run_fix_loop
from hyshell.history import HistoryStore
from hyshell.llm import Hy3Client, ShellContext
from hyshell.safety import assess_locally, merge_risk
from hyshell.schema import CommandPlan, ExecutionResult, ModelOutputError, RiskLevel, TurnRecord
from hyshell.tui import InputSource, ScriptExhausted, Tui

_MAX_GATE_ROUNDS = 6  # guards against edit/alt ping-pong loops


class GateDecision(Enum):
    RUN = "run"
    EDIT = "edit"
    ALT = "alt"
    SKIP = "skip"
    BLOCK = "block"


class ShellAssistantApp:
    """Interactive REPL / single-shot driver around the Hy3 command pipeline."""

    def __init__(
        self,
        settings: Settings,
        console: Console,
        input_source: InputSource,
        client: Hy3Client | None = None,
        workdir: Path | None = None,
        runner: Callable[..., object] | None = None,
    ) -> None:
        self.settings = settings
        self.console = console
        self.tui = Tui(console)
        self.input = input_source
        self.workdir = Path(workdir) if workdir is not None else Path.cwd()
        self.client = client or Hy3Client(settings)
        self.runner = runner or run_command
        self.ctx = ShellContext(cwd=self.workdir)
        self.history = HistoryStore(settings.home_dir)
        self.records: list[TurnRecord] = []

    # -- REPL -----------------------------------------------------------------

    def run_repl(self) -> None:
        self.tui.banner(self.settings)
        try:
            while True:
                try:
                    line = self.input.ask("[bold magenta]hyshell>[/] ").strip()
                except ScriptExhausted:
                    break
                if line in {"exit", "quit"}:
                    break
                if not line:
                    continue
                if line == "history":
                    self.tui.show_history(self.history.load_last(10))
                    continue
                self.run_turn(line)
        finally:
            self.tui.show_summary(self.records)

    # -- single turn ------------------------------------------------------------

    def run_turn(self, request: str) -> TurnRecord:
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        mode = self.settings.mode.value
        notes: list[str] = []
        try:
            plan = self.client.plan(request, self.ctx)
        except ModelOutputError as exc:
            self.tui.error(f"模型输出无法解析: {exc}")
            return self._commit(
                TurnRecord(ts, request, None, "none", None, False, None, mode, notes=["model output error"])
            )
        except OpenAIError as exc:
            self.tui.error(f"Hy3 API 调用失败: {exc}")
            return self._commit(
                TurnRecord(ts, request, None, "none", None, False, None, mode, notes=["api error"])
            )

        decision, current, final, source = self._resolve(plan, "plan", request, notes)

        if decision is GateDecision.SKIP:
            self.tui.info("已跳过,不执行。")
            return self._commit(
                TurnRecord(ts, request, current.command, source, final, False, None, mode, notes=notes)
            )
        if decision is GateDecision.BLOCK:
            return self._commit(
                TurnRecord(
                    ts, request, current.command, source, final, False, None, mode,
                    blocked=True, notes=notes,
                )
            )

        result = self._execute(current.command)
        self.tui.show_execution(result)
        fix_attempts = 0
        final_command = current.command
        if not result.ok:
            outcome = run_fix_loop(self, request, current.command, result)
            fix_attempts = outcome.attempts
            result = outcome.result
            if outcome.fixed:
                source = "fix"
                final_command = outcome.command
            elif fix_attempts:
                notes.append("修复未成功或被用户跳过")
        return self._commit(
            TurnRecord(
                ts, request, final_command, source, final, True, result.exit_code, mode,
                fix_attempts=fix_attempts, notes=notes,
            )
        )

    # -- guarded execution (shared with the fix loop) ----------------------------

    def _execute(self, command: str) -> ExecutionResult:
        """Run ``command`` through the runner; executor-level failures (spawn
        errors, undecodable output, …) become a normal failed
        :class:`ExecutionResult` instead of crashing the REPL — so rendering,
        history and the fix loop keep working."""
        started = time.monotonic()
        try:
            return self.runner(command, cwd=self.workdir)
        except (OSError, UnicodeDecodeError, subprocess.SubprocessError) as exc:
            return ExecutionResult(
                command=command,
                exit_code=EXEC_ERROR_EXIT_CODE,
                stdout="",
                stderr=f"[hyshell] 执行器异常,命令未正常完成: {type(exc).__name__}: {exc}",
                duration_s=time.monotonic() - started,
            )

    # -- assess + gate loop (shared with the fix loop) ---------------------------

    def _resolve(
        self,
        current: CommandPlan,
        source: str,
        request: str,
        notes: list[str],
    ) -> tuple[GateDecision, CommandPlan, RiskLevel, str]:
        decision = GateDecision.SKIP
        final = RiskLevel.SAFE
        for _ in range(_MAX_GATE_ROUNDS):
            findings = assess_locally(current.command)
            final, reasons = merge_risk(current.risk, current.risk_reasons, findings)
            self.tui.show_plan(current, final, reasons, source=source)
            decision = self._gate(final)
            if decision in (GateDecision.RUN, GateDecision.SKIP, GateDecision.BLOCK):
                return decision, current, final, source
            if decision is GateDecision.EDIT:
                new_command = self.input.ask("[bold]编辑命令[/] > ").strip()
                if new_command:
                    current = CommandPlan(
                        command=new_command,
                        explanation="(用户手动编辑的命令 — 仅本地安全规则评估)",
                        risk=RiskLevel.SAFE,
                        risk_reasons=[],
                    )
                    source = "edit"
                    notes.append("用户编辑了命令")
            elif decision is GateDecision.ALT:
                self.tui.info("已请求 Hy3 生成更安全的替代方案 …")
                try:
                    current = self.client.safer_alternative(current, request, self.ctx)
                except (ModelOutputError, OpenAIError) as exc:
                    self.tui.error(f"获取替代方案失败: {exc}")
                    return GateDecision.SKIP, current, final, source
                source = "alt"
                notes.append("dangerous 原方案被拦截,改用 Hy3 安全替代")
        return GateDecision.SKIP, current, final, source

    def _gate(self, level: RiskLevel) -> GateDecision:
        if self.settings.auto_yes:
            if level is RiskLevel.DANGEROUS:
                self.tui.warn("--yes 模式仍然拒绝执行 dangerous 命令(必须交互输入 RUN)。已拒绝执行。")
                return GateDecision.BLOCK
            if level is RiskLevel.CAUTION:
                self.tui.warn("--yes: caution 级命令自动放行,请留意上方风险理由。")
            return GateDecision.RUN
        if level is RiskLevel.SAFE:
            answer = self.input.ask("[green]↩ 回车执行[/] · e=编辑 · s=跳过 > ").strip().lower()
            if answer in ("", "y", "yes"):
                return GateDecision.RUN
            if answer == "e":
                return GateDecision.EDIT
            return GateDecision.SKIP
        if level is RiskLevel.CAUTION:
            answer = self.input.ask("[yellow]确认执行? y/N[/] · e=编辑 · s=跳过 > ").strip().lower()
            if answer in ("y", "yes"):
                return GateDecision.RUN
            if answer == "e":
                return GateDecision.EDIT
            return GateDecision.SKIP
        answer = self.input.ask(
            "[bold red]高危!输入 RUN 才会执行[/] · a=Hy3 安全替代 · s=跳过 > "
        ).strip()
        if answer == "RUN":
            return GateDecision.RUN
        if answer.lower() == "a":
            return GateDecision.ALT
        if answer.lower() in ("s", "skip", "exit", "quit"):
            return GateDecision.SKIP
        self.tui.warn("未输入 RUN —— 已拒绝执行该高危命令。")
        return GateDecision.BLOCK

    # -- persistence -----------------------------------------------------------

    def _commit(self, record: TurnRecord) -> TurnRecord:
        self.records.append(record)
        self.history.append(record)
        return record
