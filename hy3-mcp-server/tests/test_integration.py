import os
from pathlib import Path

import pytest
from mcp import StdioServerParameters
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

SERVER_DIR = Path(__file__).parent.parent


@pytest.fixture
def server_params():
    env = os.environ.copy()
    env["HY3_API_KEY"] = env.get("HY3_API_KEY", "test-key")
    return StdioServerParameters(
        command="python",
        args=["-m", "hy3_mcp_server.server"],
        env=env,
        cwd=str(SERVER_DIR),
    )


@pytest.mark.asyncio
async def test_list_tools(server_params):
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            names = [t.name for t in result.tools]
            assert "ask_hy3" in names, f"Missing ask_hy3. Got: {names}"
            assert "search_and_analyze" in names
            assert "file_analyze" in names


@pytest.mark.asyncio
async def test_tool_schemas_have_required_params(server_params):
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            tools_map = {t.name: t for t in result.tools}

            t = tools_map["ask_hy3"]
            assert "prompt" in t.inputSchema["properties"]
            assert "reasoning_effort" in t.inputSchema["properties"]
            assert t.inputSchema["properties"]["reasoning_effort"].get("default") == "no_think"

            t = tools_map["search_and_analyze"]
            assert "query" in t.inputSchema["properties"]
            assert "max_results" in t.inputSchema["properties"]
            assert t.inputSchema["properties"]["max_results"].get("default") == 5

            t = tools_map["file_analyze"]
            assert "file_path" in t.inputSchema["properties"]
            assert "prompt" in t.inputSchema["properties"]


@pytest.mark.asyncio
async def test_tool_descriptions_exist(server_params):
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            for t in result.tools:
                assert t.description, f"Tool {t.name} missing description"


@pytest.mark.asyncio
async def test_call_ask_hy3(server_params):
    if not os.environ.get("HY3_API_KEY") or os.environ.get("HY3_API_KEY") == "test-key":
        pytest.skip("HY3_API_KEY not set to a real key")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "ask_hy3",
                {"prompt": "What is the capital of France?", "reasoning_effort": "no_think"},
            )
            text = "".join(c.text for c in result.content if c.type == "text")
            assert "Paris" in text, f"Unexpected response: {text}"


@pytest.mark.asyncio
async def test_call_file_analyze(server_params):
    if not os.environ.get("HY3_API_KEY") or os.environ.get("HY3_API_KEY") == "test-key":
        pytest.skip("HY3_API_KEY not set to a real key")
    test_file = SERVER_DIR / "tests" / "sample.txt"
    test_file.write_text("Python is a programming language. It was created by Guido van Rossum.")
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "file_analyze",
                    {"file_path": str(test_file), "prompt": "Who created Python?"},
                )
                text = "".join(c.text for c in result.content if c.type == "text")
                assert "Guido" in text or "van Rossum" in text, f"Unexpected: {text[:200]}"
    finally:
        test_file.unlink(missing_ok=True)
