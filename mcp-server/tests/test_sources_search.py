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
"""Data source #2: pluggable search — offline stub, env-keyed Tavily."""

from __future__ import annotations

import httpx
import pytest
from mcp.server.fastmcp.exceptions import ToolError

from hy3_mcp.settings import Settings
from hy3_mcp.sources.search import (
    OfflineSearch,
    TavilySearch,
    get_search_provider,
)


def _settings(provider: str) -> Settings:
    return Settings.from_env(
        {"HY3_MCP_OFFLINE": "1", "HY3_SEARCH_PROVIDER": provider}
    )


async def test_default_provider_is_offline_and_deterministic():
    provider = get_search_provider(_settings("offline"))
    assert isinstance(provider, OfflineSearch)
    first = await provider.search("Hy3 context window", max_results=3)
    second = await provider.search("Hy3 context window", max_results=3)
    assert first == second
    assert len(first) == 3
    assert first[0].title == "Hy3 model card - Tencent Hunyuan"


async def test_offline_search_needs_no_network_or_key():
    hits = await OfflineSearch().search("model context protocol stdio", max_results=2)
    assert len(hits) == 2
    assert all(hit.url.startswith("http") for hit in hits)


def test_unknown_provider_lists_options():
    with pytest.raises(ToolError, match="offline.*tavily|tavily.*offline"):
        get_search_provider(_settings("bing"))


def test_tavily_without_key_gives_guidance(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    with pytest.raises(ToolError, match="TAVILY_API_KEY"):
        get_search_provider(_settings("tavily"))


async def test_tavily_parses_results_via_mock_transport():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/search"
        return httpx.Response(
            200,
            json={
                "results": [
                    {"title": "T1", "url": "http://a", "content": "C1"},
                    {"title": "T2", "url": "http://b", "content": "C2"},
                ]
            },
        )

    provider = TavilySearch(
        api_key="tvly-test",
        http_client=httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="https://api.tavily.com"
        ),
    )
    hits = await provider.search("q", max_results=2)
    assert [h.title for h in hits] == ["T1", "T2"]
    assert hits[0].snippet == "C1"


async def test_tavily_http_error_becomes_tool_error():
    provider = TavilySearch(
        api_key="tvly-test",
        http_client=httpx.AsyncClient(
            transport=httpx.MockTransport(lambda r: httpx.Response(401, json={})),
            base_url="https://api.tavily.com",
        ),
    )
    with pytest.raises(ToolError, match="401"):
        await provider.search("q")
