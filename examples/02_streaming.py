"""
Example 2: Streaming — stream response and parse chunks

Prerequisites:
  - Hy3 server running on port 8000
  - pip install openai
"""

from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="EMPTY")

print("Streaming response (逐 token 打印):")
print("-" * 40)

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "用 50 字以内介绍深度学习。"},
    ],
    temperature=0.9,
    max_tokens=256,
    stream=True,
)

full_content = ""
for chunk in response:
    delta = chunk.choices[0].delta
    if delta.content:
        content = delta.content
        full_content += content
        print(content, end="", flush=True)

    if chunk.choices[0].finish_reason:
        print(f"\n\n--- 最后一个 chunk ---")
        print(f"chunk.id: {chunk.id}")
        print(f"finish_reason: {chunk.choices[0].finish_reason}")
        if hasattr(chunk, 'usage') and chunk.usage:
            print(f"usage: {chunk.usage}")

print(f"\n\n完整输出:\n{full_content}")

print("\n" + "=" * 60)
print("逐 chunk 详解")
print("=" * 60)

chunk_example = """
第 1 个 chunk:
  id: "chatcmpl-xxx"
  object: "chat.completion.chunk"
  choices[0].delta: {"role": "assistant", "content": null}
  choices[0].index: 0
  choices[0].finish_reason: null

第 2 个 chunk:
  choices[0].delta: {"content": "深度"}

第 3 个 chunk:
  choices[0].delta: {"content": "学习"}

...

最后一个 chunk:
  choices[0].delta: {}
  choices[0].finish_reason: "stop"
  usage: {"prompt_tokens": 14, "completion_tokens": 32, "total_tokens": 46}
"""
print(chunk_example)
