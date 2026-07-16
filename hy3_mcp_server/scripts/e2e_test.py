"""端到端测试 - 验证 load_dataset / analyze_data / describe_chart 工具。

用法：PYTHONPATH=src python scripts/e2e_test.py
"""

import asyncio
import json
import os
import sys

from hy3_mcp_server import server


SAMPLE = os.path.join(os.path.dirname(__file__), "..", "examples", "graduate_employment_sample.csv")


async def call_tool(name: str, args: dict) -> str:
    result = await server.mcp.call_tool(name, args)
    if isinstance(result, tuple):
        content = result[0]
    else:
        content = result
    parts = []
    for c in content:
        parts.append(getattr(c, "text", str(c)))
    return "\n".join(parts)


async def main() -> None:
    print("=== Hy3 MCP Server 端到端测试 ===\n")

    print("--- load_dataset ---")
    out = await call_tool("load_dataset", {"file_path": SAMPLE})
    print(out[:600])
    assert out.strip(), "load_dataset 返回为空"
    print("\n✅ load_dataset 通过\n")

    print("--- analyze_data（模糊查询）---")
    out = await call_tool("analyze_data", {"file_path": SAMPLE, "question": "分析一下"})
    print(out[:800])
    assert out.strip(), "analyze_data 返回为空"
    print("\n✅ analyze_data 通过\n")

    print("--- describe_chart ---")
    out = await call_tool(
        "describe_chart",
        {"file_path": SAMPLE, "columns": ["专业", "实际薪资"], "chart_intent": "各专业薪资对比"},
    )
    print(out[:800])
    assert out.strip(), "describe_chart 返回为空"
    print("\n✅ describe_chart 通过\n")

    print("=== 全部测试通过 ===")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except AssertionError as e:
        print(f"❌ 断言失败: {e}")
        sys.exit(1)
