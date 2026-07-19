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
"""hy3-mcp server assembly and CLI entry point.

stdout is reserved for the MCP stdio protocol; every human-facing banner or
diagnostic goes to stderr (a hard rule — printing to stdout would corrupt
the JSON-RPC stream and break every client).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from mcp.server.fastmcp import FastMCP

from . import __version__
from .fake_backend import OFFLINE_BANNER
from .hy3_client import Hy3Client
from .settings import Settings
from .sources.files import SafeFileReader
from .tools import ToolDeps, register_all

__all__ = ["build_app", "main"]

_INSTRUCTIONS = (
    "hy3-mcp：基于腾讯 Hy3 大模型的研究与代码助手 MCP Server。提供五个工具："
    "review_code（代码评审）、ask_docs（知识库问答）、analyze_data（数据分析）、"
    "deep_research（深度研究）、hy3_status（诊断，无 LLM 调用）。"
    "未配置 HY3_API_BASE/HY3_API_KEY 时自动运行在离线演示模式（确定性 fake 后端）。 "
    "hy3-mcp: a research & code assistant MCP server powered by Tencent's Hy3 model. "
    "Five tools: review_code, ask_docs, analyze_data, deep_research and hy3_status "
    "(diagnostics, no LLM call). Without HY3_API_BASE/HY3_API_KEY it runs in an "
    "offline demo mode backed by a deterministic fake."
)


def build_app(settings: Settings | None = None) -> FastMCP:
    """Build the FastMCP app with all five tools registered."""
    settings = settings or Settings.from_env()
    app = FastMCP(name="hy3-research-assistant", instructions=_INSTRUCTIONS)
    # An explicitly configured docs dir outside HY3_MCP_ROOT becomes an
    # additional read-only sandbox root, so default ask_docs calls work.
    extra_roots = (
        () if settings.docs_dir.is_relative_to(settings.root) else (settings.docs_dir,)
    )
    deps = ToolDeps(
        settings=settings,
        client=Hy3Client(settings),
        reader=SafeFileReader(settings.root, extra_roots=extra_roots),
    )
    register_all(app, deps)
    return app


def _print_offline_banner(settings: Settings) -> None:
    if settings.mode == "offline":
        print(
            "[hy3-mcp] OFFLINE DEMO MODE (fake Hy3 backend) — set HY3_API_BASE / "
            "HY3_API_KEY for the real model",
            file=sys.stderr,
            flush=True,
        )


def _tool_result_dict(raw: object) -> dict:
    """Extract the structured dict from a ``FastMCP.call_tool()`` result.

    The return shape of ``call_tool()`` is not a stable, documented
    contract: current SDK versions return a ``(content_blocks,
    structured_output)`` tuple, while the documented/older behavior is a
    plain list of content blocks (whose first text block carries the JSON).
    Handle both so an SDK bump cannot silently break ``--selfcheck``.
    """
    if isinstance(raw, tuple):
        for part in raw:
            if isinstance(part, dict):
                return part
        raw = raw[0] if raw else raw
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, list):
        for block in raw:
            text = getattr(block, "text", None)
            if text:
                return json.loads(text)
    raise TypeError(
        f"unexpected FastMCP.call_tool() result shape: {type(raw).__name__}"
    )


async def _selfcheck_async() -> int:
    """In-process offline smoke test used by ``--selfcheck``."""
    err = sys.stderr
    settings = Settings.from_env(force_offline=True)
    app = build_app(settings)

    tools = await app.list_tools()
    names = sorted(t.name for t in tools)
    print(f"[selfcheck] tools/list -> {len(tools)} tools: {', '.join(names)}", file=err)
    if len(tools) != 5:
        print("[selfcheck] FAIL: expected 5 tools", file=err)
        return 1

    status = _tool_result_dict(await app.call_tool("hy3_status", {}))
    print(
        f"[selfcheck] hy3_status -> mode={status['mode']} model={status['model']}",
        file=err,
    )
    if status["mode"] != "offline":
        print("[selfcheck] FAIL: expected offline mode", file=err)
        return 1

    mini_diff = (
        "--- a/demo.py\n+++ b/demo.py\n@@ -1,2 +1,3 @@\n import os\n"
        "+PASSWORD = os.environ.get('APP_PASSWORD', 'hunter2')\n print('hi')\n"
    )
    review = _tool_result_dict(
        await app.call_tool("review_code", {"diff_text": mini_diff})
    )
    flags = review["heuristic_flags"]
    banner_ok = review["markdown"].startswith(OFFLINE_BANNER)
    print(
        f"[selfcheck] review_code -> {len(flags)} heuristic flag(s), "
        f"offline banner present: {banner_ok}",
        file=err,
    )
    print(f"[selfcheck] structured sample: {json.dumps(review['stats'])}", file=err)
    if not flags or not banner_ok:
        print("[selfcheck] FAIL: review_code output incomplete", file=err)
        return 1

    print("[selfcheck] PASS — hy3-mcp is installed and functional (offline mode)", file=err)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Console entry point (``hy3-mcp`` / ``python -m hy3_mcp``)."""
    parser = argparse.ArgumentParser(
        prog="hy3-mcp",
        description=(
            "Hy3 Research & Code Assistant — MCP stdio server powered by Tencent Hy3. "
            "Runs on stdio; configure via HY3_* environment variables (see README)."
        ),
    )
    parser.add_argument(
        "--version", action="store_true", help="print version and exit"
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="force the offline deterministic fake Hy3 backend",
    )
    parser.add_argument(
        "--selfcheck",
        action="store_true",
        help="run an offline in-process smoke test and exit (install verification)",
    )
    args = parser.parse_args(argv)

    if args.version:
        print(f"hy3-mcp {__version__}")
        return 0

    if args.selfcheck:
        return asyncio.run(_selfcheck_async())

    settings = Settings.from_env(force_offline=args.offline)
    _print_offline_banner(settings)
    app = build_app(settings)
    app.run(transport="stdio")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
