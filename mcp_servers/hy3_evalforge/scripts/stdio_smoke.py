"""Run a local MCP initialize/tools-list smoke test without Hy3 credentials."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    root = Path(__file__).parents[1]
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "hy3_evalforge"],
        cwd=str(root),
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print(", ".join(tool.name for tool in (await session.list_tools()).tools))


if __name__ == "__main__":
    asyncio.run(main())
