"""Hy3 Example 04: Tool calling (single call + multi-turn tool loop).

Before running against a local server, start Hy3 with a tool-call parser:
  - vLLM:  --tool-call-parser hy_v3 --reasoning-parser hy_v3 --enable-auto-tool-choice
  - SGLang: --tool-call-parser hunyuan --reasoning-parser hunyuan
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common import get_config, make_client, run_tool_loop  # noqa: E402


def get_weather(city: str) -> str:
    """Return mock weather information for a given city."""
    mock_weather = {
        "北京": "晴，气温 28°C，湿度 45%，西北风 3 级",
        "上海": "多云，气温 30°C，湿度 65%，东南风 2 级",
        "广州": "雷阵雨，气温 32°C，湿度 80%，南风 4 级",
        "深圳": "阵雨，气温 31°C，湿度 78%，南风 3 级",
    }
    return mock_weather.get(city, f"{city}：暂无天气数据（mock）")


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的实时天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "要查询天气的城市名称，例如：北京、上海",
                    }
                },
                "required": ["city"],
            },
        },
    }
]

AVAILABLE_FUNCTIONS = {
    "get_weather": get_weather,
}


def on_tool_call(tool_call, result):
    print("\n[Tool call received]")
    print(f"  tool_call_id : {tool_call.id}")
    print(f"  function     : {tool_call.function.name}")
    print(f"  arguments    : {tool_call.function.arguments}")
    print(f"\n[Executing local function {tool_call.function.name}]")
    print(f"  Result: {result}")


def main():
    cfg = get_config()
    print(f"Connecting to {cfg['base_url']}  model={cfg['model']}")
    client = make_client()

    messages = [
        {"role": "user", "content": "北京今天天气怎么样？"},
    ]
    print("=" * 70)
    print("[User Question]")
    print(messages[0]["content"])
    print("=" * 70)

    final = run_tool_loop(
        client,
        messages,
        TOOLS,
        AVAILABLE_FUNCTIONS,
        max_iterations=5,
        reasoning="no_think",
        on_tool_call=on_tool_call,
    )

    print("\n[Final Answer]")
    print(getattr(final, "content", None) if final is not None else "(no response)")
    print("=" * 70)


if __name__ == "__main__":
    main()
