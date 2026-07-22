from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from hy3_api_guardian import __version__


@pytest.mark.asyncio
async def test_stdio_initializes_and_lists_exactly_three_tools() -> None:
    project_root = Path(__file__).parents[1]
    source_root = project_root / "src"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(source_root)
    env["HY3_ALLOWED_ROOT"] = str(project_root)
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "hy3_api_guardian"],
        env=env,
    )
    async with stdio_client(parameters) as (read, write), ClientSession(read, write) as session:
        initialization = await session.initialize()
        response = await session.list_tools()

    assert initialization.serverInfo.name == "Hy3 API Guardian"
    assert initialization.serverInfo.version == __version__
    assert {tool.name for tool in response.tools} == {
        "audit_openapi",
        "detect_breaking_changes",
        "generate_contract_tests",
    }
    assert all(tool.description for tool in response.tools)
    assert all(tool.outputSchema for tool in response.tools)
    assert all(tool.annotations and tool.annotations.readOnlyHint for tool in response.tools)
    assert all(
        tool.annotations and tool.annotations.destructiveHint is False for tool in response.tools
    )
