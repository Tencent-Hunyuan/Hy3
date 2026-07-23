from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = Path(__file__).resolve().parents[1]


async def run() -> dict:
    env = os.environ.copy()
    env.setdefault("HY3_OFFLINE", "1")
    env.setdefault("HY3_LEADINTEL_ROOT", str(ROOT))
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "hy3_leadintel_mcp.server"],
        cwd=str(ROOT),
        env=env,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            tools = await session.list_tools()
            status = await session.call_tool("hy3_leadintel_status", {})
            lead = await session.call_tool(
                "analyze_lead",
                {
                    "company": "Aurora Motion GmbH",
                    "industry": "manufacturing automation",
                    "notes": "RFQ for export-ready hollow-cup motor samples and robotics validation.",
                },
            )
            return {
                "initialize": init.model_dump(mode="json"),
                "tools": tools.model_dump(mode="json"),
                "status": status.model_dump(mode="json"),
                "analyze_lead": lead.model_dump(mode="json"),
            }


def main() -> int:
    transcript = asyncio.run(run())
    out = ROOT / "assets" / "demo_transcript.json"
    serialized = json.dumps(transcript, ensure_ascii=False, indent=2)
    serialized = serialized.replace(str(ROOT), "/ABS/PATH/TO/Hy3/mcp_servers/leadintel")
    out.write_text(serialized, encoding="utf-8")
    print(json.dumps({"tool_count": len(transcript["tools"]["tools"]), "transcript": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
