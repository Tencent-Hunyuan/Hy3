import asyncio
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_stdio_initialization_lists_exactly_four_tools() -> None:
    async def check() -> None:
        package_root = Path(__file__).parents[1]
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "hy3_evalforge"],
            cwd=str(package_root),
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        async with stdio_client(parameters) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools = await session.list_tools()
                result = await session.call_tool(
                    "evalforge_design_spec",
                    {
                        "project_dir": "project",
                        "goal": "answer safely",
                        "success_criteria": "do not leak secrets",
                    },
                )

        assert {tool.name for tool in tools.tools} == {
            "evalforge_design_spec",
            "evalforge_generate_cases",
            "evalforge_score_run",
            "evalforge_compare_runs",
        }
        assert result.isError is False
        assert result.structuredContent == {
            "error": {
                "code": "CONFIG_ERROR",
                "message": (
                    "Set EVALFORGE_ALLOWED_ROOT to an existing evaluation-project root directory."
                ),
                "details": {},
            }
        }

    asyncio.run(check())
