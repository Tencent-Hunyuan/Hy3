"""示例 04：工具调用（一次调用 + 多轮工具循环）

Hy3 支持 OpenAI Function Calling：
1. 定义 tools（JSON Schema 格式的函数描述）
2. 模型返回 tool_calls 而不是直接回答
3. 在本地执行对应函数
4. 把结果以 role="tool" 消息追加回对话
5. 再次调用模型，模型据此生成最终回答

注意：本地部署需在启动时启用工具解析器：
    vLLM:   --tool-call-parser hy_v3 --enable-auto-tool-choice
    SGLang: --tool-call-parser hunyuan

运行:
    python 04_tool_calling.py
"""

import json
import os

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    timeout=int(os.environ.get("HY3_TIMEOUT_SECONDS", "60")),
)
MODEL = os.environ.get("HY3_MODEL", "hy3")
REASONING = {"chat_template_kwargs": {"reasoning_effort": "no_think"}}


# ── 1. 定义工具 ────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的当前天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，如 北京"},
                },
                "required": ["city"],
            },
        },
    }
]


# ── 2. 本地执行函数 ───
def get_weather(city: str) -> str:
    """模拟天气查询"""
    fake_db = {"北京": "晴 26°C", "上海": "多云 29°C", "深圳": "雷阵雨 31°C"}
    return fake_db.get(city, f"{city} 天气未知")


def main() -> None:
    messages = [
        {"role": "user", "content": "北京今天天气怎么样？适合户外运动吗？"},
    ]

    # ── 3. 多轮工具循环 ──
    # 最多循环 4 次，防止模型无限请求工具
    max_rounds = 4
    for round_idx in range(max_rounds):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",          # auto: 模型自行决定是否调用工具
            temperature=0.3,
            extra_body=REASONING,
        )
        msg = response.choices[0].message

        # 没有 tool_calls → 结束循环
        if not msg.tool_calls:
            print("最终回答:", msg.content)
            break

        # 把 assistant 消息（含 tool_calls）按原样加入历史
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
        })

        # 逐个执行工具调用，把结果以 role="tool" 追加
        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError as exc:
                print(f"[参数解析失败] {exc} (原始: {tc.function.arguments})")
                # 必须回填一条 role="tool" 结果，否则下一轮请求会因缺 tool 结果而 400
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": f"参数 JSON 解析失败: {exc}",
                })
                continue
            print(f"[调用工具] {name}({args})")

            if name == "get_weather":
                result = get_weather(**args)
            else:
                result = f"未知工具: {name}"

            print(f"[工具结果] {result}")
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })
    else:
        print("达到最大轮次，仍未得到最终回答。")


if __name__ == "__main__":
    main()
