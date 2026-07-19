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
"""Data source #2 — pluggable web search.

Providers implement the tiny :class:`SearchProvider` protocol and are chosen
via ``HY3_SEARCH_PROVIDER``:

* ``offline`` (default) — deterministic built-in fixtures; zero network,
  zero keys, so ``deep_research`` works out of the box and in CI.
* ``tavily`` — real web search through https://api.tavily.com/search; the
  key comes exclusively from the ``TAVILY_API_KEY`` environment variable.

Adding a provider = implement the protocol + register it in
:data:`_FACTORIES` (documented in the README "extending search" section).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx
from mcp.server.fastmcp.exceptions import ToolError

from ..settings import Settings
from .files import _tokens

__all__ = [
    "SearchHit",
    "SearchProvider",
    "OfflineSearch",
    "TavilySearch",
    "get_search_provider",
]


@dataclass(frozen=True)
class SearchHit:
    """One search result."""

    title: str
    url: str
    snippet: str


class SearchProvider:
    """Protocol-like base: a named async ``search`` method."""

    name: str = "base"

    async def search(self, query: str, max_results: int = 5) -> list[SearchHit]:
        raise NotImplementedError


#: Deterministic fixtures for the offline stub (ASCII only, demo-friendly).
_OFFLINE_FIXTURES: tuple[SearchHit, ...] = (
    SearchHit(
        title="Hy3 model card - Tencent Hunyuan",
        url="https://github.com/Tencent-Hunyuan/Hy3",
        snippet=(
            "Hy3 is a Mixture-of-Experts model (295B total / 21B active "
            "parameters) with a native 256K context window and strong agent "
            "and tool-calling capabilities."
        ),
    ),
    SearchHit(
        title="Model Context Protocol (MCP) specification",
        url="https://modelcontextprotocol.io/specification",
        snippet=(
            "MCP standardizes how AI clients connect to external tools and "
            "data sources; stdio servers exchange newline-delimited JSON-RPC "
            "messages over stdin/stdout."
        ),
    ),
    SearchHit(
        title="Serving Hy3 with vLLM",
        url="https://docs.vllm.ai/",
        snippet=(
            "An OpenAI-compatible endpoint for Hy3 can be started with vLLM "
            "using --served-model-name hy3; clients then connect to "
            "http://127.0.0.1:8000/v1 with any non-empty API key."
        ),
    ),
    SearchHit(
        title="Hy3 reasoning effort modes",
        url="https://github.com/Tencent-Hunyuan/Hy3#readme",
        snippet=(
            "Hy3 supports reasoning_effort levels no_think, low and high via "
            "chat_template_kwargs, trading latency for reasoning depth."
        ),
    ),
    SearchHit(
        title="Reducing hallucinations in LLM agents",
        url="https://example.org/hallucination-benchmarks",
        snippet=(
            "Recent releases report large drops in hallucination rate; "
            "grounding answers in retrieved evidence with citations remains "
            "the most reliable mitigation."
        ),
    ),
    SearchHit(
        title="CodeBuddy MCP integration guide",
        url="https://copilot.tencent.com/",
        snippet=(
            "CodeBuddy loads project-level MCP servers from an mcp.json file "
            "declaring the launch command and environment variables."
        ),
    ),
)


class OfflineSearch(SearchProvider):
    """Deterministic offline stub: ranks built-in fixtures by keyword overlap."""

    name = "offline"

    async def search(self, query: str, max_results: int = 5) -> list[SearchHit]:
        q = _tokens(query)
        ranked = sorted(
            enumerate(_OFFLINE_FIXTURES),
            key=lambda item: (-len(q & _tokens(item[1].title + " " + item[1].snippet)), item[0]),
        )
        return [hit for _, hit in ranked[: max(1, max_results)]]


class TavilySearch(SearchProvider):
    """Real web search via Tavily; the key comes from TAVILY_API_KEY only."""

    name = "tavily"
    endpoint = "https://api.tavily.com/search"

    def __init__(
        self,
        api_key: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        key = api_key or os.environ.get("TAVILY_API_KEY") or ""
        if not key.strip():
            raise ToolError(
                "search provider 'tavily' needs the TAVILY_API_KEY environment "
                "variable (get one at https://app.tavily.com), or set "
                "HY3_SEARCH_PROVIDER=offline to use the built-in offline stub"
            )
        self._key = key
        self._http = http_client

    async def search(self, query: str, max_results: int = 5) -> list[SearchHit]:
        payload = {"api_key": self._key, "query": query, "max_results": max_results}
        try:
            if self._http is not None:
                resp = await self._http.post(self.endpoint, json=payload)
            else:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(self.endpoint, json=payload)
        except httpx.HTTPError as exc:
            raise ToolError(f"tavily search failed: {exc}") from exc
        if resp.status_code != 200:
            raise ToolError(
                f"tavily search returned HTTP {resp.status_code}; "
                "check TAVILY_API_KEY and your quota"
            )
        results = resp.json().get("results", [])
        return [
            SearchHit(
                title=str(r.get("title", ""))[:120],
                url=str(r.get("url", "")),
                snippet=str(r.get("content", ""))[:300],
            )
            for r in results[:max_results]
        ]


_FACTORIES = {
    "offline": lambda: OfflineSearch(),
    "tavily": lambda: TavilySearch(),
}


def get_search_provider(settings: Settings) -> SearchProvider:
    """Instantiate the provider selected by ``HY3_SEARCH_PROVIDER``."""
    factory = _FACTORIES.get(settings.search_provider)
    if factory is None:
        raise ToolError(
            f"unknown search provider {settings.search_provider!r}; "
            f"valid values: {', '.join(sorted(_FACTORIES))}"
        )
    return factory()
