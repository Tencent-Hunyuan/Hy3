#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def inspect_server() -> None:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "hy3_ci_copilot"],
        env=dict(os.environ),
    )
    async with stdio_client(parameters) as (read, write), ClientSession(read, write) as session:
        initialized = await session.initialize()
        listed = await session.list_tools()
        print(
            json.dumps(
                {
                    "server": initialized.serverInfo.name,
                    "version": initialized.serverInfo.version,
                    "tools": [tool.name for tool in listed.tools],
                },
                indent=2,
            )
        )


def main() -> None:
    asyncio.run(inspect_server())


if __name__ == "__main__":
    main()
