"""Minimal MCP client that drives the hy3-security-mcp server over stdio.

This talks to the server exactly the way Cursor / CodeBuddy / Cline do — the
same MCP protocol over the same stdio transport — so it doubles as a
reproducible "used in an MCP client" demo without any IDE.

Run (needs HY3_API_KEY etc. in the environment; see .env.example):

    uv run python examples/mcp_stdio_client_demo.py

The key is read from the environment and is never printed.
"""

import asyncio
import json
import os

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

# Small pauses between calls so a screen recording (asciinema/VHS) gives each
# step its own frame; harmless (0s) when run normally.
PACE = float(os.environ.get("DEMO_PACE_SECONDS", "0"))

# Launch the real installed console-script server over stdio, inheriting the
# HY3_* config from our environment (mcp does not forward the parent env by
# default, so we pass it explicitly).
SERVER = StdioServerParameters(
    command="uv",
    args=["run", "hy3-security-mcp"],
    env=dict(os.environ),
)


async def rule(title: str) -> None:
    if PACE:
        await asyncio.sleep(PACE)
    print(f"\n\033[1;36m▶ {title}\033[0m")


def show_result(result: object) -> None:
    # A CallToolResult carries content blocks; the tools return one JSON text block.
    for block in getattr(result, "content", []):
        text = getattr(block, "text", None)
        if text is None:
            continue
        try:
            print(json.dumps(json.loads(text), ensure_ascii=False, indent=2))
        except json.JSONDecodeError:
            print(text)


async def main() -> None:
    async with stdio_client(SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            await rule("list_tools — 服务器暴露的 4 个安全工具")
            tools = await session.list_tools()
            for t in tools.tools:
                summary = (t.description or "").splitlines()[0]
                print(f"  • {t.name}: {summary}")

            await rule("audit_command  rm -rf /   （确定性快路径 · fast-path）")
            show_result(await session.call_tool("audit_command", {"command": "rm -rf /"}))

            await rule("audit_command  sudo nohup rm -rf /   （包装/别名规避仍被拦）")
            show_result(
                await session.call_tool("audit_command", {"command": "sudo nohup rm -rf /"})
            )

            await rule("audit_command  find /home -name id_rsa -exec cp …   （LLM 裁决）")
            show_result(
                await session.call_tool(
                    "audit_command",
                    {"command": r"find /home -name id_rsa -exec cp {} /tmp/harvest/ \;"},
                )
            )

            await rule("scan_secrets  （植入假密钥,原文脱敏后再交 LLM 分诊）")
            planted = 'aws_key = "AKIAIOSFODNN7EXAMPLE"\ntoken = "sk-abcdefghijklmnop1234"\n'
            show_result(await session.call_tool("scan_secrets", {"text": planted}))

            print("\n\033[1;32m✓ 全部经由真实 MCP stdio 协议往返 · all over real MCP stdio\033[0m")


if __name__ == "__main__":
    asyncio.run(main())
