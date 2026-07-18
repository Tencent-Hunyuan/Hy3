# Copyright (C) 2026 Tencent. Licensed under the Apache License, Version 2.0.
# SPDX-License-Identifier: Apache-2.0
"""Local rule-based safety engine — the second, independent line of defense.

hyshell grades every command twice:

1. the **model** (Hy3) assigns a risk level with reasons;
2. this **local rule engine** pattern-matches the command text.

The final grade is ``max(model, local)`` (:func:`merge_risk`) — the model can
*raise* the local grade but can **never lower** it.  This invariant is locked
by tests: even if a (real, non-deterministic) model claims ``safe`` for
``rm -rf /``, the local engine keeps the DANGEROUS gate shut.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from hyshell.schema import RiskLevel


@dataclass(frozen=True)
class Finding:
    """One local rule hit."""

    pattern_id: str
    level: RiskLevel
    reason_zh: str


def _regex(pattern: str, flags: int = 0) -> Callable[[str], bool]:
    compiled = re.compile(pattern, flags)
    return lambda command: compiled.search(command) is not None


# Prefix commands that merely wrap the real command (``sudo rm …``, ``xargs rm …``).
_RM_WRAPPERS = frozenset(
    {"sudo", "doas", "env", "nohup", "time", "timeout", "command", "exec", "nice", "ionice", "xargs"}
)
_ASSIGNMENT_TOKEN = re.compile(r"[A-Za-z_]\w*=\S*")
_SHORT_OPTION_GROUP = re.compile(r"-[A-Za-z]+")


def _rm_argument_tokens(segment: str) -> list[str] | None:
    """Return the argument tokens of an ``rm`` invocation in ``segment``.

    ``None`` when the segment does not *invoke* rm as a command — e.g. the
    word ``rm`` appearing as an argument of echo/grep belongs to that other
    command, not to rm."""
    tokens = segment.split()
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "rm" or token.endswith("/rm"):
            return tokens[index + 1 :]
        # skip leading VAR=… assignments, wrapper commands and their own flags
        if _ASSIGNMENT_TOKEN.fullmatch(token) or token in _RM_WRAPPERS or token.startswith("-"):
            index += 1
            continue
        return None  # a different command owns this segment
    return None


def _rm_recursive_force(command: str) -> bool:
    """rm with both recursive and force flags — any order, any position.

    GNU rm accepts options *after* operands (``rm foo -rf``), so every token
    of each rm invocation is inspected, per pipeline/list segment."""
    for segment in re.split(r"[|;&\n]+", command):
        arguments = _rm_argument_tokens(segment)
        if arguments is None:
            continue
        has_r = has_f = False
        for token in arguments:
            if token == "--":
                break  # end of options: everything after is an operand
            if token == "--recursive":
                has_r = True
            elif token == "--force":
                has_f = True
            elif _SHORT_OPTION_GROUP.fullmatch(token):
                has_r = has_r or any(char in "rR" for char in token[1:])
                has_f = has_f or "f" in token[1:]
        if has_r and has_f:
            return True
    return False


def _force_push_protected(command: str) -> bool:
    """git force-push aimed at a protected-looking branch."""
    return bool(
        re.search(r"\bgit\s+push\b", command)
        and re.search(r"--force\b|\s-f\b", command)
        and re.search(r"\b(main|master|release[\w/-]*)\b", command)
    )


# (pattern_id, level, reason_zh, matcher) — evaluated in order, all hits kept.
_RULES: tuple[tuple[str, RiskLevel, str, Callable[[str], bool]], ...] = (
    # ---------------- DANGEROUS ----------------
    (
        "rm-recursive-force",
        RiskLevel.DANGEROUS,
        "rm 递归+强制删除:不可恢复,路径/通配符一旦写错即灾难",
        _rm_recursive_force,
    ),
    (
        "no-preserve-root",
        RiskLevel.DANGEROUS,
        "显式关闭根目录保护(--no-preserve-root)",
        _regex(r"--no-preserve-root"),
    ),
    (
        "rm-system-path",
        RiskLevel.DANGEROUS,
        "删除根目录/家目录/系统顶层目录级别的路径",
        _regex(
            r"\brm\b[^|;&]*\s+("
            r"/(\*)?"
            r"|~(/(\*)?)?"
            r"|/(bin|boot|dev|etc|home|lib|lib64|opt|proc|root|sbin|srv|sys|usr|var)(/\*)?"
            r")(\s|$)"
        ),
    ),
    (
        "find-delete",
        RiskLevel.DANGEROUS,
        "find … -delete 批量永久删除匹配文件,匹配条件一旦写错即灾难",
        _regex(r"\bfind\b[^|;&]*\s-delete\b"),
    ),
    (
        "shred",
        RiskLevel.DANGEROUS,
        "shred 以多次覆写的方式销毁文件内容,数据无法恢复",
        _regex(r"\bshred\b"),
    ),
    (
        "dd-to-device",
        RiskLevel.DANGEROUS,
        "dd 直接写块设备,会摧毁其上的文件系统",
        _regex(r"\bdd\b[^|;&]*\bof=/dev/"),
    ),
    (
        "mkfs",
        RiskLevel.DANGEROUS,
        "格式化文件系统(mkfs),原有数据全部丢失",
        _regex(r"\bmkfs(\.\w+)?\b"),
    ),
    (
        "write-block-device",
        RiskLevel.DANGEROUS,
        "重定向直接写块设备节点",
        _regex(r">\s*/dev/(sd|nvme|hd|vd)"),
    ),
    (
        "fork-bomb",
        RiskLevel.DANGEROUS,
        "fork 炸弹,会耗尽系统进程资源",
        _regex(r":\s*\(\s*\)\s*\{[^}]*\|[^}]*&[^}]*\}\s*;?\s*:"),
    ),
    (
        "recursive-chmod-chown-root",
        RiskLevel.DANGEROUS,
        "对根目录递归修改权限/属主,系统会被破坏",
        _regex(r"\b(chmod|chown)\b[^|;&]*(-R\b|--recursive\b)[^|;&]*\s+/(\s|$)"),
    ),
    (
        "curl-pipe-shell",
        RiskLevel.DANGEROUS,
        "下载内容直接管道进 shell 执行,内容不可审计",
        _regex(r"\b(curl|wget)\b[^|;]*\|\s*(sudo\s+)?\S*sh\b"),
    ),
    (
        "shutdown-reboot",
        RiskLevel.DANGEROUS,
        "关机/重启会中断本机全部服务",
        _regex(r"\b(shutdown|reboot|poweroff|halt)\b"),
    ),
    (
        "kill-init",
        RiskLevel.DANGEROUS,
        "向 PID 1 发送 KILL 信号,系统会崩溃",
        _regex(r"\bkill\s+-(9|KILL)\s+1(\s|$)"),
    ),
    (
        "crontab-remove",
        RiskLevel.DANGEROUS,
        "crontab -r 会无确认清空当前用户全部定时任务",
        _regex(r"\bcrontab\s+-\w*r"),
    ),
    (
        "git-force-push-protected",
        RiskLevel.DANGEROUS,
        "向受保护分支(main/master/release)强制推送,覆盖远端历史",
        _force_push_protected,
    ),
    (
        "sql-drop",
        RiskLevel.DANGEROUS,
        "SQL DROP 语句会整表/整库删除数据",
        _regex(r"\bDROP\s+(TABLE|DATABASE|SCHEMA)\b", re.IGNORECASE),
    ),
    # ---------------- CAUTION ----------------
    (
        "sudo",
        RiskLevel.CAUTION,
        "以 root 权限执行,影响面超出当前用户",
        _regex(r"(^|[\s|&;])sudo\s"),
    ),
    (
        "mv-to-devnull",
        RiskLevel.CAUTION,
        "把文件移动到 /dev/null 等于删除",
        _regex(r"\bmv\b[^|;&]*\s+/dev/null"),
    ),
    (
        "pkill-killall",
        RiskLevel.CAUTION,
        "按名称批量杀进程,可能误伤同名进程",
        _regex(r"\b(pkill|killall)\b"),
    ),
    (
        "global-package-change",
        RiskLevel.CAUTION,
        "修改系统级/全局软件包",
        _regex(
            r"\b(apt|apt-get|yum|dnf|pacman|brew)\s+(install|remove|purge)\b"
            r"|\bnpm\s+(install|i)\s+(-g|--global)\b"
        ),
    ),
    (
        "overwrite-redirect",
        RiskLevel.CAUTION,
        "单个 > 重定向会覆盖目标文件原有内容",
        _regex(r"(?<![>\d&])>(?!>)\s*(?!/dev/null(\s|$))\S"),
    ),
)


def assess_locally(command: str) -> list[Finding]:
    """Run all local rules against ``command``; return every hit in rule order."""
    findings: list[Finding] = []
    for pattern_id, level, reason_zh, matcher in _RULES:
        if matcher(command):
            findings.append(Finding(pattern_id, level, reason_zh))
    return findings


def merge_risk(
    model_level: RiskLevel,
    model_reasons: list[str],
    findings: list[Finding],
) -> tuple[RiskLevel, list[str]]:
    """Combine model grade with local findings: ``final = max(both sides)``.

    Local reasons come first, tagged ``[本地规则 <id>]``; duplicates removed
    while preserving order.  The model can never downgrade a local finding.
    """
    local_max = max((finding.level for finding in findings), default=RiskLevel.SAFE)
    final = RiskLevel(max(model_level, local_max))
    merged = [f"[本地规则 {f.pattern_id}] {f.reason_zh}" for f in findings]
    merged += list(model_reasons)
    seen: set[str] = set()
    unique: list[str] = []
    for reason in merged:
        if reason not in seen:
            seen.add(reason)
            unique.append(reason)
    return final, unique
