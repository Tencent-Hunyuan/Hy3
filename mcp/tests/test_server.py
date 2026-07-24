from __future__ import annotations

import pytest

from hy3_deep_research.server import create_server


@pytest.mark.asyncio
async def test_server_registers_three_tools(hunyuan_env):
    mcp = create_server()
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert names == {"search_web", "fetch_url", "deep_research"}


@pytest.mark.asyncio
async def test_tools_have_descriptions(hunyuan_env):
    mcp = create_server()
    tools = {t.name: t for t in await mcp.list_tools()}
    for name in ("search_web", "fetch_url", "deep_research"):
        assert tools[name].description, f"{name} should have a description"
        assert tools[name].inputSchema is not None, f"{name} should have an input schema"
