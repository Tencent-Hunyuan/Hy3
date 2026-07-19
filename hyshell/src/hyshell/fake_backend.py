# Copyright (C) 2026 Tencent. Licensed under the Apache License, Version 2.0.
# SPDX-License-Identifier: Apache-2.0
"""Built-in deterministic fake Hy3 backend (offline demo / test mode).

The fake backend is an :class:`httpx.MockTransport` injected into the **real**
``openai`` SDK client, so the entire production code path — prompt
construction, request serialization, response parsing — is exercised
end-to-end; only the HTTP layer is replaced by an in-process handler.

Determinism guarantees (tested):

* rule tables are plain module constants, matched in order (first match wins);
* no random source anywhere; ``created`` is a fixed epoch;
* response ``id`` is derived from a SHA-1 of the prompt;
* ``usage`` token counts are pure functions of prompt/completion lengths.

The rule tables only cover the scripted demo flows and the test suite.  For
anything else the backend answers with an **honest no-op** that says so — it
never pretends to be a real model.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import httpx

FAKE_CREATED = 1700000000  # fixed timestamp: keeps responses byte-deterministic

# ---------------------------------------------------------------------------
# Rule tables (first match wins)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PlanRule:
    """Route a *plan* request: all ``keywords`` (lowercased) must appear."""

    keywords: tuple[str, ...]
    plan: dict


_FIND_PY_PLAN = {
    "command": "find . -type f -name '*.py' | wc -l",
    "explanation": "递归查找当前目录下所有 .py 文件,再用 wc -l 统计数量。",
    "risk": "safe",
    "risk_reasons": [],
    "notes": "只读操作,不修改任何文件。",
}

PLAN_RULES: tuple[PlanRule, ...] = (
    PlanRule(("多少", "python"), _FIND_PY_PLAN),
    PlanRule(("how many", "python"), _FIND_PY_PLAN),
    PlanRule(
        ("最大", "文件"),
        {
            "command": "find . -type f -printf '%s %p\\n' | sort -rn | head -n 3",
            "explanation": "列出每个文件的字节数与路径,按大小降序取前 3 个。",
            "risk": "safe",
            "risk_reasons": [],
            "notes": None,
        },
    ),
    PlanRule(
        ("日志", "删"),
        {
            "command": "rm -rf logs/*.log",
            "explanation": "递归强制删除 logs 目录下所有 .log 文件。",
            "risk": "dangerous",
            "risk_reasons": [
                "rm -rf 删除不可恢复,一旦路径或通配符写错会误删数据",
                "未先确认要删除的文件列表,存在误删风险",
            ],
            "notes": "建议先列出将被删除的文件,确认后再执行删除。",
        },
    ),
    PlanRule(
        ("report.txt", "前"),
        {
            "command": "head -n 5 report.txt",
            "explanation": "输出 report.txt 的前 5 行。",
            "risk": "safe",
            "risk_reasons": [],
            "notes": None,
        },
    ),
    PlanRule(
        ("data2",),
        {
            "command": "cat data2.csv",
            "explanation": "输出 data2.csv 的全部内容。",
            "risk": "safe",
            "risk_reasons": [],
            "notes": None,
        },
    ),
    PlanRule(
        ("locked.txt",),
        {
            "command": "cat locked.txt",
            "explanation": "输出 locked.txt 的内容。",
            "risk": "safe",
            "risk_reasons": [],
            "notes": None,
        },
    ),
    PlanRule(
        ("安装", "htop"),
        {
            "command": "sudo apt-get install -y htop",
            "explanation": "用系统包管理器安装进程监控工具 htop。",
            "risk": "caution",
            "risk_reasons": ["需要 root 权限修改系统软件包"],
            "notes": None,
        },
    ),
    PlanRule(
        ("磁盘", "占用"),
        {
            "command": "du -sh .",
            "explanation": "汇总统计当前目录占用的磁盘空间。",
            "risk": "safe",
            "risk_reasons": [],
            "notes": None,
        },
    ),
    PlanRule(
        ("强制推送",),
        {
            "command": "git push --force origin main",
            "explanation": "把本地 main 分支强制推送到远端,会覆盖远端历史。",
            "risk": "dangerous",
            "risk_reasons": ["--force 会不可逆地覆盖远端 main 分支的提交历史"],
            "notes": None,
        },
    ),
    PlanRule(
        ("列出", "隐藏"),
        {
            "command": "ls -la",
            "explanation": "列出当前目录全部文件(含隐藏文件)及详细属性。",
            "risk": "safe",
            "risk_reasons": [],
            "notes": None,
        },
    ),
)

PLAN_FALLBACK = {
    "command": "true",
    "explanation": (
        "(离线演示规则库未覆盖此请求——这是内置伪后端,"
        "接入真实 HY3_API_KEY 后可回答任意请求)"
    ),
    "risk": "safe",
    "risk_reasons": [],
    "notes": "此命令是无副作用的占位符(true)。",
}


@dataclass(frozen=True)
class FixRule:
    """Route a *fix* request by substring matching on the error context."""

    stderr_contains: str
    command_contains: str
    dir_contains: str  # "" = don't care
    fix: dict


FIX_RULES: tuple[FixRule, ...] = (
    FixRule(
        stderr_contains="No such file",
        command_contains="report.txt",
        dir_contains="report.md",
        fix={
            "diagnosis": "目录里没有 report.txt,但存在同名的 report.md —— 你要看的应是这份 Markdown 周报。",
            "command": "head -n 5 report.md",
            "risk": "safe",
            "risk_reasons": [],
            "confidence": "high",
        },
    ),
    FixRule(
        stderr_contains="No such file",
        command_contains="locked.txt",
        dir_contains="",
        fix={
            "diagnosis": "读取失败,推测是残留锁目录导致;可强制清理锁目录后重试。",
            "command": "sudo rm -rf locked_dir",
            "risk": "caution",
            "risk_reasons": ["会递归删除 locked_dir 目录"],
            "confidence": "low",
        },
    ),
    FixRule(
        stderr_contains="No such file",
        command_contains="data",
        dir_contains="",
        fix={
            "diagnosis": "找不到目标数据文件,猜测存在备份文件 data_backup.csv,尝试读取它。",
            "command": "cat data_backup.csv",
            "risk": "safe",
            "risk_reasons": [],
            "confidence": "low",
        },
    ),
)

FIX_FALLBACK = {
    "diagnosis": (
        "(离线演示规则库无法诊断此错误——这是内置伪后端,"
        "接入真实 HY3_API_KEY 后可诊断任意错误)先列出目录内容辅助人工排查。"
    ),
    "command": "ls -la",
    "risk": "safe",
    "risk_reasons": [],
    "confidence": "low",
}


@dataclass(frozen=True)
class AltRule:
    """Route an *alt* (safer alternative) request by rejected-command substring."""

    rejected_contains: str
    alt: dict


ALT_RULES: tuple[AltRule, ...] = (
    AltRule(
        rejected_contains="rm -rf logs",
        alt={
            "command": "find logs -name '*.log' -mtime +30 -print",
            "explanation": "只读列出 30 天前的旧日志文件,不做任何删除;人工确认列表后再决定是否清理。",
            "risk": "caution",
            "risk_reasons": ["后续若把 -print 换成 -delete 才会真正删除,请先核对列表"],
            "notes": "确认无误后可运行: find logs -name '*.log' -mtime +30 -delete",
        },
    ),
)

ALT_FALLBACK = {
    "command": "echo '(离线规则库无替代方案,请人工审阅原命令)'",
    "explanation": "(离线演示规则库没有该命令的安全替代——内置伪后端的诚实兜底)",
    "risk": "safe",
    "risk_reasons": [],
    "notes": None,
}

# ---------------------------------------------------------------------------
# Envelope parsing + routing
# ---------------------------------------------------------------------------


def _parse_fields(user_content: str) -> dict[str, str]:
    """Parse the ``## NAME: value`` envelope; values may span multiple lines."""
    fields: dict[str, str] = {}
    current: str | None = None
    for line in user_content.splitlines():
        if line.startswith("## ") and ":" in line:
            name, _, value = line[3:].partition(":")
            current = name.strip()
            fields[current] = value.strip()
        elif current is not None:
            fields[current] += "\n" + line
    return fields


def _route_plan(request: str) -> dict:
    low = request.lower()
    for rule in PLAN_RULES:
        if all(k.lower() in low for k in rule.keywords):
            return rule.plan
    return PLAN_FALLBACK


def _route_fix(fields: dict[str, str]) -> dict:
    stderr = fields.get("STDERR", "")
    command = fields.get("COMMAND", "")
    listing = fields.get("DIR", "")
    for rule in FIX_RULES:
        if (
            rule.stderr_contains in stderr
            and rule.command_contains in command
            and (not rule.dir_contains or rule.dir_contains in listing)
        ):
            return rule.fix
    return FIX_FALLBACK


def _route_alt(fields: dict[str, str]) -> dict:
    rejected = fields.get("REJECTED", "")
    for rule in ALT_RULES:
        if rule.rejected_contains in rejected:
            return rule.alt
    return ALT_FALLBACK


class FakeHy3:
    """Deterministic in-process stand-in for the Hy3 chat.completions API."""

    def handle(self, request: httpx.Request) -> httpx.Response:
        if not request.url.path.endswith("/chat/completions"):
            return httpx.Response(
                404, json={"error": {"message": f"fake backend: unknown path {request.url.path}"}}
            )
        body = json.loads(request.content.decode("utf-8"))
        user = ""
        for message in reversed(body.get("messages", [])):
            if message.get("role") == "user":
                user = message.get("content", "")
                break
        task = None
        for line in user.splitlines():
            if line.startswith("## TASK:"):
                task = line.split(":", 1)[1].strip()
                break
        if task == "plan":
            content = json.dumps(_route_plan(_parse_fields(user).get("REQUEST", "")), ensure_ascii=False)
        elif task == "fix":
            content = json.dumps(_route_fix(_parse_fields(user)), ensure_ascii=False)
        elif task == "alt":
            content = json.dumps(_route_alt(_parse_fields(user)), ensure_ascii=False)
        else:
            content = "pong (fake Hy3 backend)"
        return httpx.Response(200, json=self._completion(user, content, body.get("model", "hy3")))

    @staticmethod
    def _completion(user: str, content: str, model: str) -> dict:
        digest = hashlib.sha1(user.encode("utf-8")).hexdigest()[:8]
        prompt_tokens = len(user) // 4
        completion_tokens = len(content) // 4
        return {
            "id": f"chatcmpl-fake-{digest}",
            "object": "chat.completion",
            "created": FAKE_CREATED,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content},
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }


def make_fake_transport() -> httpx.MockTransport:
    """Transport to plug into the real openai SDK client (offline mode)."""
    return httpx.MockTransport(FakeHy3().handle)
