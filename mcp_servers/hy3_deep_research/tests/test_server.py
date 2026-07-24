from __future__ import annotations

import pytest

from hy3_deep_research.models import SearchResult
from hy3_deep_research.server import create_server

from test_service import make_service


@pytest.mark.asyncio
async def test_server_exposes_four_described_tools() -> None:
    service, _ = make_service(
        [SearchResult(title="One", url="https://example.com", snippet="evidence")],
        {},
    )
    server = create_server(service)

    tools = await server.list_tools()
    by_name = {tool.name: tool for tool in tools}

    assert set(by_name) == {
        "search_web",
        "analyze_evidence",
        "deep_research",
        "verify_claim",
    }
    assert all(tool.description for tool in tools)
    assert by_name["deep_research"].inputSchema["properties"]["query"]["description"]
    assert by_name["analyze_evidence"].inputSchema["properties"]["sources"][
        "description"
    ]
