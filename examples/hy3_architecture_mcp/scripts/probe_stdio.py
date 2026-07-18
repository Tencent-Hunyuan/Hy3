"""Probe the stdio MCP server using the official MCP client SDK.

This is the canonical integration path used by CodeBuddy/Cursor/Cline etc.,
so a green result here is strong evidence the server is client-compatible.

Exit code 0 on success, non-zero on failure.
"""

import asyncio
import sys
import traceback

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

EXPECTED = {
    "clarify_requirements",
    "generate_technical_proposal",
    "review_technical_proposal",
    "create_implementation_plan",
    "analyze_project_context",
}


async def main() -> int:
    # Allow overriding the launch command to verify both invocation paths:
    #   python scripts/probe_stdio.py                  # -> python -m hy3_architecture_mcp
    #   python scripts/probe_stdio.py hy3-architecture-mcp
    argv = sys.argv[1:]
    if argv:
        command, args = argv[0], argv[1:]
    else:
        command, args = "python", ["-m", "hy3_architecture_mcp"]
    params = StdioServerParameters(
        command=command,
        args=args,
        env=None,  # inherit; server reads HY3_* at tool-call time, not startup
    )
    try:
        async with (
            stdio_client(params) as (read, write),
            ClientSession(read, write) as session,
        ):
            init_result = await session.initialize()
            server_info = init_result.serverInfo
            print(f"initialize OK: {server_info.name} v{server_info.version}")

            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            print(f"TOOLS VIA STDIO ({len(names)}): {names}")
            for tool in tools.tools:
                desc = (tool.description or "").splitlines()[0][:90]
                print(f"  - {tool.name}: {desc}")

            missing = EXPECTED - set(names)
            if missing:
                print(f"MISSING TOOLS: {missing}")
                return 1
            print("ALL 5 EXPECTED TOOLS PRESENT")
            return 0
    except BaseException as exc:  # noqa: BLE001
        print(f"PROBE FAILED: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        eg = getattr(exc, "exceptions", None)
        if eg:
            for sub in eg:
                print(f"  sub-exception: {type(sub).__name__}: {sub}")
        return 2


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
