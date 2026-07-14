from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()
client = OpenAI(
    api_key=os.getenv("API_KEY", "EMPTY"),
    base_url=os.getenv("BASE_URL", "http://127.0.0.1:8000/v1")
)



def streaming_chat():
    print("=== 流式请求 + 逐 Chunk 解析示例 ===")

    print("\n【完整请求参数】")
    print(f"  model: hy3")
    print(f"  messages: [{{'role': 'user', 'content': '请用简短的语言介绍 Python 的主要特点'}}]")
    print(f"  temperature: 0.9")
    print(f"  top_p: 1.0")
    print(f"  stream: True")

    stream = client.chat.completions.create(
        model="hy3",
        messages=[
            {"role": "user", "content": "请用简短的语言介绍 Python 的主要特点"},
        ],
        temperature=0.9,
        top_p=1.0,
        stream=True,
    )

    print("\n【逐 Chunk 解析过程】")
    full_content = ""
    chunk_count = 0
    finish_reason = None

    for chunk in stream:
        chunk_count += 1

        print(f"\n--- Chunk #{chunk_count} ---")
        print(f"  id: {chunk.id}")
        print(f"  object: {chunk.object}")
        print(f"  created: {chunk.created}")
        print(f"  model: {chunk.model}")

        if chunk.choices:
            choice = chunk.choices[0]
            delta = choice.delta

            print(f"  choices[0]:")
            print(f"    finish_reason: {choice.finish_reason}")
            print(f"    delta:")

            if delta.role:
                print(f"      ├─ role: {delta.role}")
            if delta.content:
                print(f"      └─ content: '{delta.content}'")
                full_content += delta.content

            if choice.finish_reason:
                finish_reason = choice.finish_reason

    print(f"\n【解析结果汇总】")
    print(f"  总 Chunk 数: {chunk_count}")
    print(f"  finish_reason: {finish_reason}")
    print(f"  完整回复内容长度: {len(full_content)} 字符")

    print("\n【示例输出】")
    print(f"Assistant: {full_content}")


def streaming_with_tool_calls():
    print("\n\n=== 流式请求 + 工具调用示例 ===")

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "获取指定城市的天气信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "城市名称"},
                    },
                    "required": ["city"],
                },
            },
        }
    ]

    print("\n【完整请求参数】")
    print(f"  model: hy3")
    print(f"  messages: [{{'role': 'user', 'content': '北京今天天气怎么样？'}}]")
    print(f"  tools: [{len(tools)} 个工具]")
    print(f"  stream: True")

    stream = client.chat.completions.create(
        model="hy3",
        messages=[
            {"role": "user", "content": "北京今天天气怎么样？"},
        ],
        tools=tools,
        stream=True,
    )

    print("\n【逐 Chunk 解析 - 工具调用】")
    full_tool_calls = []
    chunk_count = 0

    for chunk in stream:
        chunk_count += 1
        print(f"\n--- Chunk #{chunk_count} ---")

        if chunk.choices:
            choice = chunk.choices[0]
            delta = choice.delta

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    print(f"  delta.tool_calls:")
                    print(f"    index: {tc.index}")
                    print(f"    id: {tc.id}")
                    print(f"    type: {tc.type}")
                    if tc.function:
                        print(f"    function:")
                        if tc.function.name:
                            print(f"      ├─ name: {tc.function.name}")
                        if tc.function.arguments:
                            print(f"      └─ arguments: '{tc.function.arguments}'")


if __name__ == "__main__":
    streaming_chat()
    streaming_with_tool_calls()