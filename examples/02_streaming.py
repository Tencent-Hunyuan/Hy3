"""
Hy3 API - 流式输出示例 / Streaming Example
逐 chunk 解析流式响应
"""

from openai import OpenAI

# ============================================================
# 配置 / Configuration
# ============================================================
BASE_URL = "http://127.0.0.1:8000/v1"
API_KEY = "EMPTY"
MODEL = "hy3"

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


# ============================================================
# 示例 1：基础流式输出 / Basic Streaming
# ============================================================
def basic_streaming():
    """最简单的流式输出：逐字符打印"""
    print("=" * 60)
    print("基础流式输出 / Basic Streaming")
    print("=" * 60)

    stream = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "用 Python 写一个快速排序算法。"},
        ],
        temperature=0.9,
        top_p=1.0,
        stream=True,
    )

    full_content = ""
    print("\n回复：", end="")

    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            print(delta.content, end="", flush=True)
            full_content += delta.content

    print(f"\n\n完整内容长度：{len(full_content)} 字符")


# ============================================================
# 示例 2：完整的流式解析 / Full Stream Parsing
# ============================================================
def full_stream_parsing():
    """解析每个 chunk 的完整信息：role、content、finish_reason"""
    print("\n" + "=" * 60)
    print("完整流式解析 / Full Stream Parsing")
    print("=" * 60)

    stream = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "什么是Mixture of Experts（MoE）架构？"},
        ],
        temperature=0.9,
        top_p=1.0,
        stream=True,
    )

    full_content = ""
    print("\n回复：", end="")

    for chunk in stream:
        choice = chunk.choices[0]

        # 第一个 chunk 通常包含 role 信息
        if choice.delta.role:
            print(f"\n[角色: {choice.delta.role}]", end="")

        # 内容增量
        if choice.delta.content:
            print(choice.delta.content, end="", flush=True)
            full_content += choice.delta.content

        # 最后一个 chunk 包含 finish_reason
        if choice.finish_reason:
            print(f"\n\n[结束原因: {choice.finish_reason}]")

    print(f"[总字符数: {len(full_content)}]")


# ============================================================
# 示例 3：流式收集到变量 / Collect Stream to Variable
# ============================================================
def collect_stream():
    """将流式输出收集到变量，用于后续处理"""
    print("\n" + "=" * 60)
    print("流式收集 / Collect Stream")
    print("=" * 60)

    stream = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "写一首关于春天的五言绝句。"},
        ],
        temperature=0.9,
        top_p=1.0,
        stream=True,
    )

    # 收集所有 chunk
    chunks = []
    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            chunks.append(delta.content)

    full_content = "".join(chunks)
    print(f"\n完整回复：\n{full_content}")
    print(f"\n共收到 {len(chunks)} 个 chunk")


# ============================================================
# 运行示例
# ============================================================
if __name__ == "__main__":
    basic_streaming()
    full_stream_parsing()
    collect_stream()
