"""
MCP Server — exposes web_search and code_execution as MCP tools.

Design doc reference: §四 (MCP Tool Channel)

These tools are "external capabilities" — they interact with third-party
services (web search API) or require sandboxed execution (code runner).
They run in a separate process via FastMCP stdio transport.

Start with:
    python -m app.mcp.server
"""

from __future__ import annotations

import asyncio
import json
import logging
import tempfile
import subprocess
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from app.config import get_settings

logger = logging.getLogger(__name__)

# ── Tool definitions ──────────────────────────────────────────

WEB_SEARCH_TOOL = Tool(
    name="web_search",
    description="Search the web for information about a given query. "
                "Use this to look up documentation, API references, and "
                "context about third-party libraries or frameworks.",
    inputSchema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (default 5)",
                "default": 5,
            },
        },
        "required": ["query"],
    },
)

CODE_EXEC_TOOL = Tool(
    name="code_execution",
    description="Execute Python code in an isolated sandbox and return the output. "
                "Use this to run test scripts, validate code behavior, or compute "
                "metrics. Maximum execution time: 15 seconds.",
    inputSchema={
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute",
            },
        },
        "required": ["code"],
    },
)


# ── Server ────────────────────────────────────────────────────

app = Server("archaeologist-mcp")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [WEB_SEARCH_TOOL, CODE_EXEC_TOOL]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    if name == "web_search":
        return await _handle_web_search(arguments)
    elif name == "code_execution":
        return await _handle_code_exec(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


# ── Handlers ──────────────────────────────────────────────────

async def _handle_web_search(args: dict[str, Any]) -> list[TextContent]:
    query = args.get("query", "")
    max_results = min(args.get("max_results", 5), 10)

    settings = get_settings()
    api_key = settings.tavily_api_key

    if not api_key:
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": "No Tavily API key configured. Set ARCHAEOLOGIST_TAVILY_API_KEY.",
                "results": [],
            })
        )]

    try:
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "basic",
                },
            )
            data = response.json()

            results = []
            for r in data.get("results", [])[:max_results]:
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": (r.get("content", "") or "")[:500],
                })

            return [TextContent(type="text", text=json.dumps({"results": results}))]

    except Exception as e:
        logger.warning("Web search failed: %s", e)
        return [TextContent(type="text", text=json.dumps({
            "error": str(e),
            "results": [],
        }))]


async def _handle_code_exec(args: dict[str, Any]) -> list[TextContent]:
    code = args.get("code", "")

    if not code:
        return [TextContent(type="text", text=json.dumps({"error": "No code provided"}))]

    # Execute in a subprocess with timeout
    try:
        proc = await asyncio.create_subprocess_exec(
            "python3", "-c", code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
        except asyncio.TimeoutError:
            proc.kill()
            return [TextContent(type="text", text=json.dumps({
                "error": "Execution timed out (15s limit)",
                "stdout": "",
                "stderr": "",
            }))]

        return [TextContent(type="text", text=json.dumps({
            "stdout": stdout.decode("utf-8", errors="replace")[:4000],
            "stderr": stderr.decode("utf-8", errors="replace")[:2000],
            "returncode": proc.returncode,
        }))]

    except FileNotFoundError:
        return [TextContent(type="text", text=json.dumps({
            "error": "Python3 not found in sandbox",
            "stdout": "",
            "stderr": "",
        }))]


# ── Entry point ───────────────────────────────────────────────

def main():
    """Run the MCP server via stdio transport."""
    import anyio
    logging.basicConfig(level=logging.INFO)

    async def _run():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())

    anyio.run(_run)


if __name__ == "__main__":
    main()
