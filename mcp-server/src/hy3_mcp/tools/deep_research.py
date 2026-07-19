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
"""deep_research — multi-source evidence collection + Hy3 synthesis."""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import Field

from ..prompts import research_prompts
from ..schemas import Evidence, ResearchReport
from ..sources.search import get_search_provider
from . import ToolDeps, safe_info, safe_progress

__all__ = ["register"]

_SNIPPET_CHARS = 400


def register(app: FastMCP, deps: ToolDeps) -> None:
    @app.tool(
        name="deep_research",
        description=(
            "深度研究：通过可插拔搜索源（默认离线 stub，可选 Tavily）与沙箱内本地材料收集证据，"
            "由 Hy3 综合产出带编号引用的研究结论。 "
            "Deep research: gathers evidence from the pluggable search source (offline stub "
            "by default, Tavily with an env key) plus local files in the sandbox, then asks "
            "Hy3 for a cited synthesis."
        ),
    )
    async def deep_research(
        topic: Annotated[
            str,
            Field(description="研究主题或问题。 The research topic or question."),
        ],
        source_paths: Annotated[
            list[str],
            Field(
                default_factory=list,
                description=(
                    "沙箱内补充材料文件路径列表（可空）。 "
                    "Optional list of sandbox-relative files to use as extra sources."
                ),
            ),
        ],
        use_search: Annotated[
            bool,
            Field(
                description=(
                    "是否调用搜索数据源（由 HY3_SEARCH_PROVIDER 决定具体后端）。 "
                    "Whether to query the search data source (backend chosen by "
                    "HY3_SEARCH_PROVIDER)."
                )
            ),
        ] = True,
        max_sources: Annotated[
            int,
            Field(
                ge=1,
                le=8,
                description="搜索结果条数上限（1-8）。 Max search results to collect (1-8).",
            ),
        ] = 5,
        ctx: Context = None,  # type: ignore[assignment]
    ) -> ResearchReport:
        if not topic.strip():
            raise ToolError("topic must not be empty")

        evidence: list[Evidence] = []
        provider_name = "none"

        await safe_progress(ctx, 1, 3)
        if use_search:
            provider = get_search_provider(deps.settings)
            provider_name = provider.name
            hits = await provider.search(topic, max_results=max_sources)
            evidence.extend(
                Evidence(
                    kind="search",
                    ref=f"{hit.title} <{hit.url}>",
                    snippet=hit.snippet[:_SNIPPET_CHARS],
                )
                for hit in hits
            )
            await safe_info(
                ctx, f"deep_research: {len(hits)} hit(s) from provider {provider_name!r}"
            )

        await safe_progress(ctx, 2, 3)
        for user_path in source_paths:
            text = deps.reader.read_text(user_path)
            evidence.append(
                Evidence(kind="file", ref=user_path, snippet=text[:_SNIPPET_CHARS])
            )

        if not evidence:
            raise ToolError(
                "no evidence collected: enable use_search or provide source_paths "
                "(refusing to synthesize without sources)"
            )

        system, user = research_prompts(topic, evidence)
        reply = await deps.client.chat(
            task="research", system=system, user=user, reasoning_effort="high"
        )
        await safe_progress(ctx, 3, 3)
        return ResearchReport(
            markdown=reply.text,
            evidence=evidence,
            search_provider=provider_name,
            mode=deps.settings.mode,
        )
