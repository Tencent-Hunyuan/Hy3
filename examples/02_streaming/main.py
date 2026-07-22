"""
对应Issue要求：streaming（流式请求+逐chunk解析）
效果：模型内容逐字输出，类似ChatGPT的打字机效果
"""
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_API_KEY",
    base_url="https://tokenhub.tencentmaas.com/v1"
)

print("=== 流式对话测试（逐chunk解析）===")
print("模型回复：", end="", flush=True)

stream = client.chat.completions.create(
    model="hy3-preview",
    messages=[
        {"role": "user", "content": "写一段300字左右的科幻小说开头"}
    ],
    stream=True,  # 开启流式
    temperature=0.8,
    max_tokens=400
)

# 逐chunk解析并输出
full_content = ""
chunk_count = 0
for chunk in stream:
    chunk_count += 1
    if chunk.choices and chunk.choices[0].delta.content:
        content = chunk.choices[0].delta.content
        full_content += content
        print(content, end="", flush=True)  # 实时打印，无缓冲
    
    # 解析最后一个chunk的usage信息
    if chunk.choices and chunk.choices[0].finish_reason == "stop":
        if hasattr(chunk, "usage") and chunk.usage:
            print(f"\n\n=== 流式响应统计 ===")
            print(f"总chunk数：{chunk_count}")
            print(f"Token消耗：输入{chunk.usage.prompt_tokens}，输出{chunk.usage.completion_tokens}")

print("\n=== 流式输出结束 ===")