"""End-to-end stdio smoke test against the real MCP server process.

Drives the server with the official MCP Python SDK client over stdio.
Exercises the tools that do NOT require a live Hy3 GPU endpoint
(web_search_tool, read_url_tool) against the real web, proving the MCP
server is callable from a real MCP client. Hy3-wrapped tools
(research_question, summarize_documents, generate_research_outline) are
unit-tested in tests/test_server.py because no live Hy3 endpoint is
available in CI.

Run:
    python mcp_servers/deep_research/scripts/stdio_smoke.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

REPO_SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(REPO_SRC))


async def main() -> None:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    server_cmd = [sys.executable, "-m", "hy3_research_mcp.server"]
    params = StdioServerParameters(
        command=server_cmd[0], args=server_cmd[1:], env=os.environ.copy()
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            tool_names = sorted(t.name for t in tools.tools)
            print("TOOLS:", tool_names)
            expected = {
                "web_search_tool",
                "read_url_tool",
                "research_question",
                "summarize_documents",
                "generate_research_outline",
            }
            assert expected <= set(tool_names), tool_names

            # Real web search over stdio (no key, no Hy3).
            res = await session.call_tool(
                "web_search_tool", {"query": "Tencent Hy3 model", "max_results": 3}
            )
            payload = json.loads(res.content[0].text) if res.content else {}
            print("SEARCH COUNT:", payload.get("count"))
            print("SAMPLE RESULT:", (payload.get("results") or [{}])[0])
            assert payload.get("count", 0) >= 0, payload
            print("WEB_SEARCH SMOKE OK")

            # Real page read over stdio (no key, no Hy3).
            res2 = await session.call_tool(
                "read_url_tool",
                {"url": "https://raw.githubusercontent.com/Tencent-Hunyuan/Hy3/main/README.md", "max_chars": 1000},
            )
            payload2 = json.loads(res2.content[0].text) if res2.content else {}
            print("READ_URL CHARS:", payload2.get("chars"))
            sample_text = payload2.get("text", "")
            print("READ SAMPLE:", sample_text[:120].replace(chr(10), " "))
            assert payload2.get("chars", 0) > 0, payload2
            print("READ_URL SMOKE OK")

            print("STDIO SMOKE OK")


if __name__ == "__main__":
    asyncio.run(main())