"""Launch the packaged server over stdio and verify discovery plus a real tool call."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TOOLS = {"profile_dataset", "analyze_dataset", "generate_data_report"}


async def check() -> None:
    env = dict(os.environ)
    env["HY3_DATA_DIR"] = str(PACKAGE_ROOT)
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "hy3_data_analyst"],
        env=env,
    )

    async with (
        stdio_client(params) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        listed = await session.list_tools()
        names = {tool.name for tool in listed.tools}
        if names != EXPECTED_TOOLS:
            raise RuntimeError(f"unexpected tools: {sorted(names)}")
        print(f"MCP initialize: OK ({len(names)} tools)")
        print("Tools: " + ", ".join(sorted(names)))

        result = await session.call_tool(
            "profile_dataset",
            {"file_path": "examples/sample_sales.csv", "sample_rows": 2},
        )
        if result.isError:
            raise RuntimeError(f"profile_dataset failed: {result.content}")
        text = result.content[0].text
        if '"rows_scanned":6' not in text.replace(" ", ""):
            raise RuntimeError(f"unexpected profile result: {text}")
        print("profile_dataset: OK (6 rows, sample_rows=2)")


def main() -> None:
    asyncio.run(check())


if __name__ == "__main__":
    main()
