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
"""hy3_status — zero-cost diagnostics: backend mode, config and usage."""

from __future__ import annotations

from mcp.server.fastmcp import Context, FastMCP

from .. import __version__
from ..schemas import ServerInfo, UsageStats
from . import ToolDeps

__all__ = ["register"]


def register(app: FastMCP, deps: ToolDeps) -> None:
    @app.tool(
        name="hy3_status",
        description=(
            "诊断：报告服务器版本、后端模式（offline/real）、API 端点、模型名、搜索源、"
            "沙箱根目录与累计用量；不调用 LLM，适合作为客户端接入后的第一个演示调用。 "
            "Diagnostics: reports server version, backend mode (offline/real), API base, "
            "model, search provider, sandbox root and cumulative usage; makes no LLM call, "
            "ideal as the first demo call after connecting a client."
        ),
    )
    async def hy3_status(ctx: Context = None) -> ServerInfo:  # type: ignore[assignment]
        settings = deps.settings
        return ServerInfo(
            server_version=__version__,
            protocol="MCP/stdio",
            mode=settings.mode,
            api_base=settings.api_base,
            api_key_present=settings.api_key_present,
            model=settings.model,
            search_provider=settings.search_provider,
            sandbox_root=str(settings.root),
            usage=UsageStats(**deps.client.usage.as_dict()),
        )
