# Copyright 2026 Tencent Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""review_code — Hy3-powered code review of a unified diff or source file."""

from __future__ import annotations

import re
from typing import Annotated, Literal

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import Field

from ..prompts import review_prompts
from ..schemas import DiffStats, Flag, ReviewResult
from . import ToolDeps, safe_info

__all__ = ["register", "parse_unified_diff", "scan_heuristics"]

_HUNK_RE = re.compile(r"@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

#: (category, severity, message) — first matching rule wins per line.
_RULES: tuple[tuple[str, str, str], ...] = (
    ("security", "high", "possible hardcoded credential"),
    ("correctness", "medium", "fragile construct (eval / == None)"),
    ("maintainability", "low", "leftover TODO/FIXME marker"),
    ("style", "low", "line exceeds 120 characters"),
)


def parse_unified_diff(text: str) -> tuple[DiffStats, list[tuple[str, int, str]]]:
    """Parse a unified diff deterministically.

    Returns the :class:`DiffStats` plus the list of added lines as
    ``(file, new_line_number, content)`` tuples for heuristic scanning.

    Hunk bodies are consumed according to the line counts declared in the
    ``@@`` header, so removed lines whose content starts with ``--``
    (rendered ``---…``) or added lines starting with ``++`` (rendered
    ``+++…``) are never mistaken for ``---``/``+++`` file headers.
    """
    files: list[str] = []
    hunks = added = removed = 0
    added_lines: list[tuple[str, int, str]] = []
    current_file = ""
    new_lineno = 0
    old_left = new_left = 0  # unconsumed old/new lines of the current hunk

    for line in text.splitlines():
        if old_left > 0 or new_left > 0:  # inside a hunk body
            if line.startswith("\\"):  # "\ No newline at end of file"
                continue
            if line.startswith("+"):
                added += 1
                added_lines.append((current_file, new_lineno, line[1:]))
                new_lineno += 1
                new_left -= 1
            elif line.startswith("-"):
                removed += 1
                old_left -= 1
            else:  # context line (possibly empty)
                new_lineno += 1
                new_left -= 1
                old_left -= 1
            continue
        if line.startswith("+++ "):
            name = line[4:].split("\t")[0].strip()
            if name.startswith("b/"):
                name = name[2:]
            if name != "/dev/null":
                current_file = name
                files.append(name)
        elif line.startswith("@@"):
            match = _HUNK_RE.match(line)
            if match is not None:
                hunks += 1
                old_left = int(match.group(1) or 1)
                new_lineno = int(match.group(2))
                new_left = int(match.group(3) or 1)

    stats = DiffStats(
        files=files, hunks=hunks, added_lines=added, removed_lines=removed
    )
    return stats, added_lines


def _match_rule(line: str) -> tuple[str, str, str] | None:
    low = line.lower()
    if "password" in low or "secret" in low:
        return _RULES[0]
    if "eval(" in line or "== None" in line or "!= None" in line:
        return _RULES[1]
    if "TODO" in line or "FIXME" in line:
        return _RULES[2]
    if len(line) > 120:
        return _RULES[3]
    return None


def scan_heuristics(lines: list[tuple[str, int, str]]) -> list[Flag]:
    """Deterministic pre-review scan; first matching rule wins per line."""
    flags: list[Flag] = []
    for file, lineno, content in lines:
        rule = _match_rule(content)
        if rule is not None:
            category, severity, message = rule
            flags.append(
                Flag(
                    category=category,  # type: ignore[arg-type]
                    severity=severity,  # type: ignore[arg-type]
                    file=file or "(inline)",
                    line=lineno,
                    message=f"{message}: {content.strip()[:80]}",
                )
            )
    return flags


def register(app: FastMCP, deps: ToolDeps) -> None:
    @app.tool(
        name="review_code",
        description=(
            "代码评审：读取 unified diff 或沙箱内源码文件，由 Hy3 输出按严重程度排序的评审意见，"
            "并附带确定性的 diff 统计与启发式风险标记。 "
            "Code review: reads a unified diff (or a source file inside the sandbox) and asks "
            "Hy3 for a severity-ordered review, plus deterministic diff stats and heuristic risk flags."
        ),
    )
    async def review_code(
        diff_text: Annotated[
            str,
            Field(
                description=(
                    "Unified diff 文本（直接粘贴）；与 path 二选一。 "
                    "Unified diff text pasted inline; give exactly one of diff_text / path."
                )
            ),
        ] = "",
        path: Annotated[
            str,
            Field(
                description=(
                    "沙箱根内 diff 或源码文件的相对路径；与 diff_text 二选一。 "
                    "Path (relative to the sandbox root) of a diff or source file; "
                    "give exactly one of diff_text / path."
                )
            ),
        ] = "",
        focus: Annotated[
            Literal["all", "correctness", "security", "style"],
            Field(
                description=(
                    "评审侧重点。 Review focus: all (default), correctness, security or style."
                )
            ),
        ] = "all",
        ctx: Context = None,  # type: ignore[assignment]
    ) -> ReviewResult:
        if bool(diff_text.strip()) == bool(path.strip()):
            raise ToolError(
                "provide exactly one of diff_text (inline diff) or path (sandboxed file)"
            )
        text = deps.reader.read_text(path) if path.strip() else diff_text

        stats, added_lines = parse_unified_diff(text)
        if stats.hunks == 0:  # plain source file, not a diff: scan every line
            label = path.strip() or "(inline)"
            stats = DiffStats(files=[label], hunks=0, added_lines=0, removed_lines=0)
            added_lines = [
                (label, i, line) for i, line in enumerate(text.splitlines(), start=1)
            ]

        flags = scan_heuristics(added_lines)
        if focus != "all":
            flags = [f for f in flags if f.category == focus]

        await safe_info(ctx, f"review_code: {len(flags)} heuristic flag(s), asking Hy3")
        system, user = review_prompts(text, stats, focus)
        reply = await deps.client.chat(
            task="review", system=system, user=user, reasoning_effort="high"
        )
        return ReviewResult(
            markdown=reply.text,
            stats=stats,
            heuristic_flags=flags,
            model=reply.model,
            mode=deps.settings.mode,
        )
