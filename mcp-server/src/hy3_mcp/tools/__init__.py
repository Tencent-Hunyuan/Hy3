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
"""Tool registration for the hy3-mcp FastMCP app."""

from __future__ import annotations

from dataclasses import dataclass

from mcp.server.fastmcp import Context, FastMCP

from ..hy3_client import Hy3Client
from ..settings import Settings
from ..sources.files import SafeFileReader

__all__ = ["ToolDeps", "register_all", "safe_info", "safe_progress"]


@dataclass
class ToolDeps:
    """Shared dependencies injected into every tool closure."""

    settings: Settings
    client: Hy3Client
    reader: SafeFileReader


async def safe_info(ctx: Context | None, message: str) -> None:
    """Send an MCP log message; never fail outside a live request context."""
    if ctx is None:
        return
    try:
        await ctx.info(message)
    except (ValueError, RuntimeError):  # no active request (e.g. --selfcheck)
        pass


async def safe_progress(ctx: Context | None, current: float, total: float) -> None:
    """Report progress; never fail outside a live request context."""
    if ctx is None:
        return
    try:
        await ctx.report_progress(current, total)
    except (ValueError, RuntimeError):
        pass


def register_all(app: FastMCP, deps: ToolDeps) -> None:
    """Register the five tools (order defines the tools/list order)."""
    from . import analyze_data, ask_docs, deep_research, review_code, status

    review_code.register(app, deps)
    ask_docs.register(app, deps)
    analyze_data.register(app, deps)
    deep_research.register(app, deps)
    status.register(app, deps)
