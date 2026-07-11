"""Hy3 Code Review MCP Server.

Exposes three tools:
  - review_diff      : Review a git diff (text or file path)
  - analyze_file     : Deep analysis of a source code file
  - git_diff_review  : Auto-run `git diff` in a repo and produce a full report
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import mcp.server.stdio
import mcp.types as types
from mcp.server import Server
import openai
from openai import OpenAI

# ---------------------------------------------------------------------------
# Hy3 client
# ---------------------------------------------------------------------------

def _is_local_host(host: str) -> bool:
    return host in ("localhost", "127.0.0.1", "::1", "[::1]")


def _get_client() -> OpenAI:
    base_url = os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
    api_key = os.environ.get("HY3_API_KEY", "EMPTY")
    # Warn (over stderr, never stdout — stdout is the MCP protocol channel) if
    # credentials + code would be sent over plaintext HTTP to a non-local host.
    parsed = urlparse(base_url)
    if parsed.scheme == "http" and not _is_local_host(parsed.hostname or ""):
        print(
            f"[hy3] WARNING: HY3_BASE_URL uses plaintext http:// to non-local host "
            f"{parsed.hostname!r}; API key and code are sent unencrypted. Use https://.",
            file=sys.stderr,
        )
    return OpenAI(base_url=base_url, api_key=api_key)


def _get_model() -> str:
    return os.environ.get("HY3_MODEL", "hy3")


_EMPTY_RESPONSE_NOTICE = (
    "**Hy3 返回了空响应**（`:free` 档偶发限流或冷启动）。"
    "请稍后重试，或将 HY3_MODEL 设为付费模型。"
)


def _extract_content(content: str | None, reasoning: str | None) -> str:
    if (content or "").strip():
        return content
    if (reasoning or "").strip():
        return (
            "> ⚠️ Hy3 未返回正式结论，以下为其推理过程草稿：\n\n"
            f"{reasoning}"
        )
    return _EMPTY_RESPONSE_NOTICE


def _friendly_error(exc: Exception) -> str:
    if isinstance(exc, openai.RateLimitError):
        return (
            "**Hy3 端点限流（429）**。`:free` 档常见，"
            "请稍后重试，或将 HY3_MODEL 设为付费模型。"
        )
    return f"**Hy3 调用失败**：{type(exc).__name__}: {exc}"


def _call_hy3(
    system_prompt: str,
    user_content: str,
    reasoning_effort: str = "high",
    max_tokens: int = 4096,
) -> str:
    client = _get_client()
    try:
        response = client.chat.completions.create(
            model=_get_model(),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.9,
            top_p=1.0,
            max_tokens=max_tokens,
            extra_body={"chat_template_kwargs": {"reasoning_effort": reasoning_effort}},
        )
    except Exception as exc:
        return _friendly_error(exc)

    msg = response.choices[0].message
    content = msg.content
    reasoning = getattr(msg, "reasoning", None)
    return _extract_content(content, reasoning)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

REVIEW_DIFF_SYSTEM = """\
You are an expert code reviewer. Your goal is to identify real bugs, security issues, \
logic errors, and meaningful improvement opportunities in the provided diff. \
Be precise and evidence-based — cite exact line numbers or code snippets. \
Do NOT fabricate issues that are not present in the diff.

Output format (Markdown):

## Summary
One-paragraph overview of the change and overall quality.

## Issues Found
For each issue:
- **[Severity: CRITICAL|HIGH|MEDIUM|LOW]** `<file>:<line>` — Description and why it matters.
  - Suggested fix: ...

## Positive Highlights
Brief mention of what was done well.

## Verdict
APPROVE / REQUEST CHANGES / NEEDS DISCUSSION
"""

ANALYZE_FILE_SYSTEM = """\
You are an expert software engineer performing a thorough code review of a single file. \
Analyze it for the requested focus areas. Be specific and cite line numbers. \
Do NOT hallucinate issues that do not exist.

Output format (Markdown):

## File Overview
Language, purpose, key structures.

## Findings
Grouped by focus area. Each finding: severity, location, explanation, suggested fix.

## Summary
Top 3 action items in priority order.
"""

GIT_DIFF_REVIEW_SYSTEM = """\
You are a senior engineer performing a pre-merge code review. \
You will be given the output of `git diff`. Identify real bugs, regressions, \
security vulnerabilities, and style/API inconsistencies. \
Cite specific file paths and line numbers. Never invent findings.

Output format (Markdown):

## Changed Files
Brief inventory of what changed.

## Critical Issues
Blockers that must be fixed before merge.

## Minor Issues & Suggestions
Non-blocking improvements.

## Test Coverage Gaps
Areas lacking test coverage given the diff.

## Verdict
APPROVE / REQUEST CHANGES / NEEDS DISCUSSION
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Max file size to read (bytes). Guards against feeding huge files to the LLM.
_MAX_FILE_BYTES = 2 * 1024 * 1024  # 2 MiB

# Valid git ref: alphanumerics, slash, dot, dash, underscore. Must not start
# with '-' (blocks argument injection like `--upload-pack=...`).
_VALID_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")


def _allowed_roots() -> list[Path]:
    """Optional sandbox. If HY3_ALLOWED_ROOTS is set (os.pathsep-separated),
    file reads are restricted to those directories. Unset = no restriction."""
    raw = os.environ.get("HY3_ALLOWED_ROOTS", "").strip()
    if not raw:
        return []
    return [Path(r).expanduser().resolve() for r in raw.split(os.pathsep) if r.strip()]


def _read_file(path: str) -> str:
    # Resolve symlinks and normalize before any check (blocks symlink escape).
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not p.is_file():
        raise ValueError(f"Not a regular file: {path}")

    roots = _allowed_roots()
    if roots and not any(p == r or r in p.parents for r in roots):
        raise PermissionError(
            "Access denied: path is outside HY3_ALLOWED_ROOTS."
        )

    size = p.stat().st_size
    if size > _MAX_FILE_BYTES:
        raise ValueError(
            f"File too large ({size} bytes > {_MAX_FILE_BYTES} limit)."
        )
    return p.read_text(encoding="utf-8", errors="replace")


def _run_git_diff(repo_path: str, base_branch: str) -> str:
    if not _VALID_REF.match(base_branch):
        raise ValueError(
            f"Invalid base_branch {base_branch!r}: must match {_VALID_REF.pattern}"
        )
    # --no-ext-diff blocks external diff drivers; GIT_CONFIG_NOSYSTEM +
    # disabling core.pager/ext-diff blocks RCE via a malicious repo config.
    env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_PAGER": "cat"}
    result = subprocess.run(
        ["git", "-c", "core.fsmonitor=false", "diff", "--no-ext-diff",
         "--stat", "--patch", base_branch, "--"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git diff failed: {result.stderr.strip()}")
    output = result.stdout.strip()
    if not output:
        result2 = subprocess.run(
            ["git", "-c", "core.fsmonitor=false", "diff", "--no-ext-diff",
             "--stat", "--patch", "HEAD", "--"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
        )
        output = result2.stdout.strip()
    return output


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

server = Server("hy3-code-review-mcp")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="review_diff",
            description=(
                "Review a git diff using Hy3. Accepts either the diff text directly "
                "or a path to a .diff/.patch file. Returns a structured Markdown report "
                "with severity-tagged issues, suggestions, and a merge verdict."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "diff": {
                        "type": "string",
                        "description": "The git diff text to review. Takes precedence over diff_file if both are provided.",
                    },
                    "diff_file": {
                        "type": "string",
                        "description": "Path to a .diff or .patch file. Used only when 'diff' is not provided.",
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional: brief description of what this change is about.",
                    },
                    "reasoning_effort": {
                        "type": "string",
                        "enum": ["no_think", "low", "high"],
                        "default": "high",
                        "description": "Hy3 reasoning depth. Use 'high' for thorough review, 'no_think' for quick scan.",
                    },
                },
            },
        ),
        types.Tool(
            name="analyze_file",
            description=(
                "Perform a deep analysis of a single source code file using Hy3. "
                "Detects bugs, security vulnerabilities, performance issues, and style problems. "
                "Returns a Markdown report with per-line findings and prioritized action items."
            ),
            inputSchema={
                "type": "object",
                "required": ["file_path"],
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute or relative path to the source code file.",
                    },
                    "focus": {
                        "type": "string",
                        "enum": ["security", "performance", "style", "bugs", "all"],
                        "default": "all",
                        "description": "What to focus on.",
                    },
                    "reasoning_effort": {
                        "type": "string",
                        "enum": ["no_think", "low", "high"],
                        "default": "high",
                        "description": "Hy3 reasoning depth.",
                    },
                },
            },
        ),
        types.Tool(
            name="git_diff_review",
            description=(
                "Automatically run `git diff <base_branch>` in a local repository and "
                "generate a full code review report using Hy3. "
                "Ideal for pre-merge checks inside a development workflow."
            ),
            inputSchema={
                "type": "object",
                "required": ["repo_path"],
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Absolute path to the local git repository.",
                    },
                    "base_branch": {
                        "type": "string",
                        "default": "main",
                        "description": "Base branch to diff against (e.g. 'main', 'master', 'develop').",
                    },
                    "reasoning_effort": {
                        "type": "string",
                        "enum": ["no_think", "low", "high"],
                        "default": "high",
                        "description": "Hy3 reasoning depth.",
                    },
                },
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict
) -> list[types.TextContent]:
    try:
        if name == "review_diff":
            result = await _tool_review_diff(arguments)
        elif name == "analyze_file":
            result = await _tool_analyze_file(arguments)
        elif name == "git_diff_review":
            result = await _tool_git_diff_review(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
    except Exception as exc:
        # Log full detail server-side (stderr); return a generic message so
        # filesystem paths / git internals are not leaked to the caller.
        print(f"[hy3-mcp] tool {name!r} failed: {type(exc).__name__}: {exc}",
              file=sys.stderr, flush=True)
        result = f"**工具执行失败**（{type(exc).__name__}）。详情见服务端日志。"

    return [types.TextContent(type="text", text=result)]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

async def _tool_review_diff(args: dict) -> str:
    diff_text: str = args.get("diff", "")
    diff_file: str = args.get("diff_file", "")
    context: str = args.get("context", "")
    reasoning_effort: str = args.get("reasoning_effort", "high")

    if not diff_text and diff_file:
        diff_text = _read_file(diff_file)
    if not diff_text:
        raise ValueError("Provide either 'diff' text or 'diff_file' path.")

    user_content = diff_text
    if context:
        user_content = f"**Change context**: {context}\n\n---\n\n{diff_text}"

    # Hy3 has 256K context — safe to pass large diffs directly
    return _call_hy3(
        system_prompt=REVIEW_DIFF_SYSTEM,
        user_content=user_content,
        reasoning_effort=reasoning_effort,
    )


async def _tool_analyze_file(args: dict) -> str:
    file_path: str = args["file_path"]
    focus: str = args.get("focus", "all")
    reasoning_effort: str = args.get("reasoning_effort", "high")

    source_code = _read_file(file_path)
    filename = Path(file_path).name

    focus_instruction = {
        "security": "Focus ONLY on security vulnerabilities (injection, auth, crypto, exposure).",
        "performance": "Focus ONLY on performance issues (complexity, memory, I/O, concurrency).",
        "style": "Focus ONLY on code style, naming, readability, and maintainability.",
        "bugs": "Focus ONLY on logic errors, null dereferences, off-by-one errors, and crashes.",
        "all": "Cover all areas: security, performance, style, and bugs.",
    }.get(focus, "Cover all areas.")

    system = ANALYZE_FILE_SYSTEM + f"\n\n{focus_instruction}"
    user_content = f"**File**: `{filename}`\n\n```\n{source_code}\n```"

    return _call_hy3(
        system_prompt=system,
        user_content=user_content,
        reasoning_effort=reasoning_effort,
        max_tokens=8192,
    )


async def _tool_git_diff_review(args: dict) -> str:
    repo_path: str = args["repo_path"]
    base_branch: str = args.get("base_branch", "main")
    reasoning_effort: str = args.get("reasoning_effort", "high")

    diff_text = _run_git_diff(repo_path, base_branch)
    if not diff_text:
        return f"No changes detected between current branch and `{base_branch}`."

    user_content = (
        f"**Repository**: `{repo_path}`\n"
        f"**Base branch**: `{base_branch}`\n\n"
        f"```diff\n{diff_text}\n```"
    )

    return _call_hy3(
        system_prompt=GIT_DIFF_REVIEW_SYSTEM,
        user_content=user_content,
        reasoning_effort=reasoning_effort,
        max_tokens=8192,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def _run() -> None:
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    import asyncio
    asyncio.run(_run())


if __name__ == "__main__":
    main()
