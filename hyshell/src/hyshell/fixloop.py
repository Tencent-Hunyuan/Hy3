# Copyright (C) 2026 Tencent. Licensed under the Apache License, Version 2.0.
# SPDX-License-Identifier: Apache-2.0
"""Error → Hy3 diagnosis → confirm → retry loop (agentic error recovery).

Every fix suggestion passes through the exact same safety assessment and
confirmation gate as a first-shot plan — a dangerous "fix" still requires the
user to type ``RUN``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from openai import OpenAIError

from hyshell.schema import CommandPlan, ExecutionResult, ModelOutputError

if TYPE_CHECKING:  # pragma: no cover - import cycle guard, typing only
    from hyshell.app import ShellAssistantApp

DIR_LISTING_LIMIT = 30


@dataclass
class FixOutcome:
    """What the fix loop achieved."""

    result: ExecutionResult
    attempts: int
    fixed: bool
    command: str


def dir_listing(path: Path, limit: int = DIR_LISTING_LIMIT) -> str:
    """Deterministic directory context for the fix prompt (sorted, capped)."""
    entries = sorted(os.listdir(path))[:limit]
    return " ".join(entries) if entries else "(空目录)"


def run_fix_loop(
    app: "ShellAssistantApp",
    request: str,
    failed_command: str,
    failed_result: ExecutionResult,
) -> FixOutcome:
    """Ask Hy3 to repair a failed command, gate it, retry — up to max retries."""
    from hyshell.app import GateDecision  # local import to avoid a cycle

    result = failed_result
    command = failed_command
    attempts = 0
    max_retries = app.settings.max_fix_retries
    while attempts < max_retries:
        attempts += 1
        app.tui.info(
            f"命令失败(exit {result.exit_code}),请求 Hy3 诊断修复(第 {attempts}/{max_retries} 次)…"
        )
        try:
            suggestion = app.client.suggest_fix(
                request, command, result, dir_listing(app.workdir), app.ctx
            )
        except (ModelOutputError, OpenAIError) as exc:
            app.tui.error(f"获取修复建议失败: {exc}")
            break
        app.tui.show_fix(suggestion)
        fix_plan = CommandPlan(
            command=suggestion.command,
            explanation=suggestion.diagnosis,
            risk=suggestion.risk,
            risk_reasons=suggestion.risk_reasons,
        )
        decision, current, _final, _source = app._resolve(fix_plan, "fix", request, [])
        if decision is not GateDecision.RUN:
            if decision is GateDecision.SKIP:
                app.tui.info("已跳过修复命令。")
            return FixOutcome(result=result, attempts=attempts, fixed=False, command=command)
        new_result = app._execute(current.command)
        app.tui.show_execution(new_result)
        if new_result.ok:
            app.tui.success(f"修复成功(第 {attempts} 次重试)")
            return FixOutcome(result=new_result, attempts=attempts, fixed=True, command=current.command)
        result = new_result
        command = current.command
    else:
        app.tui.warn("已达最大修复重试次数,放弃自动修复。")
    return FixOutcome(result=result, attempts=attempts, fixed=False, command=command)
