"""Test script to verify logging output in stderr."""
import asyncio
import os

from dotenv import load_dotenv
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "src", ".env"))

from fastmcp import Client
from hy3_mcp_server.server import mcp


async def test_server():
    async with Client(mcp) as client:
        tools = await client.list_tools()
        print(f"Found {len(tools)} tools")

        # Test read_file - should show log
        print("\n--- Calling read_file ---")
        result = await client.call_tool("read_file", {"file_path": "README.md"})
        print(f"Got {len(str(result))} chars")

        # Test summarize_document - should show log with timing
        print("\n--- Calling summarize_document ---")
        result = await client.call_tool("summarize_document", {
            "file_path": "README.md",
            "summary_type": "brief",
            "max_length": 100
        })
        text = str(result)
        print(f"Got {len(text)} chars")


if __name__ == "__main__":
    asyncio.run(test_server())
