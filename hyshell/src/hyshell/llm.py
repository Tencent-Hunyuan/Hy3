# Copyright (C) 2026 Tencent. Licensed under the Apache License, Version 2.0.
# SPDX-License-Identifier: Apache-2.0
"""The single gateway between hyshell and the Hy3 model.

Everything the model does for hyshell goes through :class:`Hy3Client` and the
OpenAI-compatible ``chat.completions`` API — there is **no** training, no
finetune and no local inference anywhere in this project.  Hy3 is called at
four points:

1. ``plan``  — natural language → shell command + explanation + risk grade;
2. ``alt``   — safer alternative for a rejected dangerous command;
3. ``fix``   — diagnose a failed command (exit code + stderr + dir listing)
   and propose a repaired command;
4. ``ping``  — trivial roundtrip used by ``hyshell doctor --ping``.

The strict single-JSON-object output contract leans directly on the Hy3
README's advertised strength: *"Stability of tool calls and output formats …
production-grade standards across tool configurations and output
constraints"*.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import httpx
from openai import OpenAI

from hyshell.config import BackendMode, Settings
from hyshell.fake_backend import make_fake_transport
from hyshell.schema import CommandPlan, ExecutionResult, FixSuggestion, ModelOutputError

FAKE_BASE_URL = "http://fake.hy3.local/v1"
STDERR_TAIL_CHARS = 800

# --------------------------------------------------------------------------
# System prompts (Chinese; strict JSON contract)
# --------------------------------------------------------------------------

_JSON_CONTRACT = (
    "输出要求(必须严格遵守):只输出一个 JSON 对象,不要输出任何其他文字、"
    "Markdown 围栏或注释。"
)

_RISK_RUBRIC = (
    "危险分级 rubric:删除/覆盖数据、写块设备、改系统全局状态、需要 root 的"
    "不可逆操作 → \"dangerous\";有副作用但影响范围可控(sudo 安装、杀进程、"
    "覆盖单个文件)→ \"caution\";只读或仅新建文件 → \"safe\"。"
)

PLAN_SYSTEM_PROMPT = (
    "你是 hyshell,一个把自然语言需求转换为单条 Linux shell 命令的终端助手。"
    "绝不虚构不存在的工具,优先使用 POSIX/GNU coreutils。"
    f"{_RISK_RUBRIC}"
    f"{_JSON_CONTRACT}"
    "JSON 字段:command(单条 bash 命令), explanation(中文解释命令做什么), "
    "risk(\"safe\"|\"caution\"|\"dangerous\"), risk_reasons(中文理由数组,safe 可为空数组), "
    "notes(可选补充说明,没有则为 null)。"
)

FIX_SYSTEM_PROMPT = (
    "你是 hyshell 的错误诊断器。给你一条执行失败的 shell 命令及其退出码、"
    "stderr 与当前目录列表,请诊断失败原因并给出修复后的命令。"
    "只根据给出的证据诊断,不要臆测不存在的文件。"
    f"{_RISK_RUBRIC}"
    f"{_JSON_CONTRACT}"
    "JSON 字段:diagnosis(中文诊断), command(修复后的单条 bash 命令), "
    "risk, risk_reasons, confidence(\"high\"|\"medium\"|\"low\")。"
)

ALT_SYSTEM_PROMPT = (
    "你是 hyshell 的安全顾问。用户拒绝了一条高危 shell 命令,请给出一个更安全的"
    "替代方案,优先给只读的第一步(先列出会被影响的对象,再由人决定)。"
    f"{_RISK_RUBRIC}"
    f"{_JSON_CONTRACT}"
    "JSON 字段:command, explanation, risk, risk_reasons, notes。"
)


@dataclass
class ShellContext:
    """Ambient facts injected into every prompt envelope."""

    cwd: Path
    os_name: str = "Linux"


# --------------------------------------------------------------------------
# Prompt envelope builders (shared verbatim by real and fake backends)
# --------------------------------------------------------------------------


def build_plan_messages(request: str, ctx: ShellContext) -> list[dict]:
    user = (
        f"## TASK: plan\n## CWD: {ctx.cwd}\n## OS: {ctx.os_name}\n"
        f"## REQUEST: {request}"
    )
    return [
        {"role": "system", "content": PLAN_SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def build_fix_messages(
    request: str,
    failed_command: str,
    result: ExecutionResult,
    dir_listing: str,
    ctx: ShellContext,
) -> list[dict]:
    stderr_tail = result.stderr[-STDERR_TAIL_CHARS:]
    user = (
        f"## TASK: fix\n## CWD: {ctx.cwd}\n## OS: {ctx.os_name}\n"
        f"## REQUEST: {request}\n## COMMAND: {failed_command}\n"
        f"## EXIT: {result.exit_code}\n## STDERR: {stderr_tail}\n"
        f"## DIR: {dir_listing}"
    )
    return [
        {"role": "system", "content": FIX_SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def build_alt_messages(plan: CommandPlan, request: str, ctx: ShellContext) -> list[dict]:
    reasons = "; ".join(plan.risk_reasons) or "(无)"
    user = (
        f"## TASK: alt\n## CWD: {ctx.cwd}\n## OS: {ctx.os_name}\n"
        f"## REQUEST: {request}\n## REJECTED: {plan.command}\n"
        f"## RISK_REASONS: {reasons}"
    )
    return [
        {"role": "system", "content": ALT_SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


# --------------------------------------------------------------------------
# Tolerant JSON extraction
# --------------------------------------------------------------------------

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json_block(text: str) -> dict:
    """Extract the first balanced JSON object from a model reply.

    Tolerates Markdown code fences, surrounding prose and whitespace.  Raises
    :class:`ModelOutputError` (with a snippet of the raw text) when no valid
    object can be found — so misbehaving real-model output stays debuggable.
    """
    candidate = text.strip()
    fenced = _FENCE_RE.search(candidate)
    if fenced:
        candidate = fenced.group(1).strip()
    start = candidate.find("{")
    if start == -1:
        raise ModelOutputError(f"模型输出中没有 JSON 对象: {candidate[:200]!r}")
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(candidate)):
        char = candidate[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                block = candidate[start : index + 1]
                try:
                    parsed = json.loads(block)
                except json.JSONDecodeError as exc:
                    raise ModelOutputError(
                        f"JSON 解析失败 ({exc}): {block[:200]!r}"
                    ) from exc
                if not isinstance(parsed, dict):
                    raise ModelOutputError(f"模型输出不是 JSON 对象: {block[:200]!r}")
                return parsed
    raise ModelOutputError(f"模型输出中的 JSON 对象不完整: {candidate[:200]!r}")


# --------------------------------------------------------------------------
# Client
# --------------------------------------------------------------------------


class Hy3Client:
    """Thin, typed wrapper around the OpenAI-compatible Hy3 endpoint.

    In FAKE mode the client is wired to the in-process deterministic fake
    transport; in REAL mode it talks to ``settings.api_base`` (self-hosted
    vLLM/SGLang or the Tencent Cloud endpoint).  Tests may inject a spy
    ``transport`` to observe the raw HTTP traffic.
    """

    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None) -> None:
        self._settings = settings
        if settings.mode is BackendMode.FAKE:
            transport = transport or make_fake_transport()
            base_url = FAKE_BASE_URL
            max_retries = 0
        else:
            base_url = settings.api_base
            max_retries = 2
        http_client = httpx.Client(transport=transport) if transport is not None else None
        self._client = OpenAI(
            api_key=settings.api_key,
            base_url=base_url,
            http_client=http_client,
            timeout=settings.request_timeout,
            max_retries=max_retries,
        )

    # -- public API ---------------------------------------------------------

    def plan(self, request: str, ctx: ShellContext) -> CommandPlan:
        """Natural-language request → structured command plan."""
        data = extract_json_block(self._chat(build_plan_messages(request, ctx)))
        return self._validate(CommandPlan, data)

    def suggest_fix(
        self,
        request: str,
        failed_command: str,
        result: ExecutionResult,
        dir_listing: str,
        ctx: ShellContext,
    ) -> FixSuggestion:
        """Failed execution → diagnosis + repaired command."""
        messages = build_fix_messages(request, failed_command, result, dir_listing, ctx)
        data = extract_json_block(self._chat(messages))
        return self._validate(FixSuggestion, data)

    def safer_alternative(self, plan: CommandPlan, request: str, ctx: ShellContext) -> CommandPlan:
        """Rejected dangerous command → safer alternative plan."""
        data = extract_json_block(self._chat(build_alt_messages(plan, request, ctx)))
        return self._validate(CommandPlan, data)

    def ping(self) -> str:
        """Minimal roundtrip for ``hyshell doctor --ping``."""
        response = self._client.chat.completions.create(
            model=self._settings.model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=16,
            temperature=0,
        )
        return (response.choices[0].message.content or "").strip()

    # -- internals ----------------------------------------------------------

    def _chat(self, messages: list[dict]) -> str:
        kwargs: dict = {
            "model": self._settings.model,
            "messages": messages,
            "temperature": self._settings.temperature,
            "top_p": self._settings.top_p,
        }
        if self._settings.reasoning_effort:
            kwargs["extra_body"] = {
                "chat_template_kwargs": {"reasoning_effort": self._settings.reasoning_effort}
            }
        response = self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    @staticmethod
    def _validate(model_cls, data: dict):
        try:
            return model_cls.model_validate(data)
        except Exception as exc:  # pydantic.ValidationError
            raise ModelOutputError(
                f"模型 JSON 不满足 {model_cls.__name__} 契约: {exc}"
            ) from exc
