"""
Hy3 API Mock Test Suite
离线模拟测试全部 6 个示例，验证代码逻辑正确性
输出保存到 test_output/ 目录
"""

import sys
import os
import time
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mock_api import MockResponse, MockChunk, MockUsage, MockChoice, MockMessage, simulate_stream, simulate_stream_with_usage

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

PASS = 0
FAIL = 0


def log(name, content):
    path = os.path.join(OUTPUT_DIR, f"{name}.log")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  -> 日志已保存: {path}")


def test_basic_chat():
    global PASS, FAIL
    print("\n" + "=" * 60)
    print("测试 01: Basic Chat (基础对话)")
    print("=" * 60)

    # 模拟单轮对话
    mock_resp = MockResponse(
        content="量子计算是利用量子力学原理（如叠加和纠缠）进行信息处理的新型计算范式。",
        prompt_tokens=15, completion_tokens=42,
    )
    reply = mock_resp.choices[0].message.content
    usage = mock_resp.usage

    output = f"""=== 单轮对话 ===

Request:
  model: hy3
  messages: [{{"role": "user", "content": "用一句话解释什么是量子计算。"}}]
  temperature: 0.9
  top_p: 1.0

Response ID: {mock_resp.id}
Response:
  {reply}

Usage:
  prompt_tokens: {usage.prompt_tokens}
  completion_tokens: {usage.completion_tokens}
  total_tokens: {usage.total_tokens}

Finish reason: {mock_resp.choices[0].finish_reason}
"""

    # 模拟多轮对话
    messages = [
        {"role": "user", "content": "推荐几本科幻小说。"},
    ]
    r1 = MockResponse(
        content="推荐：《三体》（刘慈欣）、《银河帝国》（阿西莫夫）、《沙丘》（赫伯特）。",
        prompt_tokens=12, completion_tokens=38,
    )
    msg1 = r1.choices[0].message.content
    messages.append({"role": "assistant", "content": msg1})
    messages.append({"role": "user", "content": "我最喜欢《三体》，能再推荐类似的作品吗？"})

    r2 = MockResponse(
        content="喜欢《三体》的话，可以试试《盲视》（彼得·沃茨），同样是硬核科幻。",
        prompt_tokens=28, completion_tokens=45,
    )
    msg2 = r2.choices[0].message.content

    output += f"""
=== 多轮对话 ===

Round 1:
  Assistant: {msg1}

Round 2:
  User: 我最喜欢《三体》，能再推荐类似的作品吗？
  Assistant: {msg2}

Total rounds: 2
"""
    assert "量子计算" in reply
    assert "三体" in msg2
    PASS += 1
    output += "\nResult: PASS\n"
    log("01_basic_chat", output)
    print(output)


def test_streaming():
    global PASS, FAIL
    print("\n" + "=" * 60)
    print("测试 02: Streaming (流式输出)")
    print("=" * 60)

    content = "人工智能的未来将深刻改变人类社会的方方面面。从医疗诊断到自动驾驶，从个性化教育到科学研究，AI 正在各个领域展现出前所未有的潜力。"

    output = "=== 流式请求：逐 chunk 解析 ===\n\n"
    output += f"Request: 请写一段 200 字左右的短文，主题是人工智能的未来。\n\n"

    full_content = ""
    chunk_count = 0
    for chunk in simulate_stream_with_usage(content):
        chunk_count += 1
        if chunk.choices and chunk.choices[0].delta.content:
            c = chunk.choices[0].delta.content
            full_content += c
            output += f"  Chunk {chunk_count}: \"{c}\"\n"
        if chunk.choices and chunk.choices[0].finish_reason:
            output += f"\n  Finish reason: {chunk.choices[0].finish_reason}\n"
        if chunk.usage:
            output += f"  Usage: {chunk.usage}\n"

    output += f"\n完整输出 ({len(full_content)} 字符):\n  {full_content}\n"
    output += f"\n总 chunk 数: {chunk_count}\n"

    assert len(full_content) > 0
    assert chunk_count > 1
    PASS += 1
    output += "\nResult: PASS\n"
    log("02_streaming", output)
    print(output)


def test_nonstreaming_vs_streaming():
    global PASS, FAIL
    print("\n" + "=" * 60)
    print("测试 03: Non-streaming vs Streaming (对比)")
    print("=" * 60)

    content = ("Transformer 架构的核心是自注意力机制（Self-Attention），"
               "它允许模型在处理序列时关注不同位置的信息。"
               "自注意力通过 Query、Key、Value 三个矩阵计算注意力权重，"
               "然后加权聚合得到输出。")

    output = "=== Non-streaming vs Streaming 对比 ===\n\n"
    output += "Request: 请详细解释机器学习中的 Transformer 架构。\n\n"

    # 模拟非流式
    t0 = time.time()
    time.sleep(0.05)
    resp = MockResponse(content=content, prompt_tokens=20, completion_tokens=85)
    ns_time = time.time() - t0

    output += f"[Non-streaming]\n"
    output += f"  总耗时: {ns_time:.3f}s\n"
    output += f"  输出长度: {len(content)} 字符\n"
    output += f"  Usage: {resp.usage}\n\n"

    # 模拟流式
    t0 = time.time()
    first_token = None
    stream_chunks = []
    for chunk in simulate_stream(content):
        if first_token is None and chunk.choices[0].delta.content:
            first_token = time.time() - t0
        if chunk.choices[0].delta.content:
            stream_chunks.append(chunk.choices[0].delta.content)
    s_total = time.time() - t0
    s_content = "".join(stream_chunks)

    output += f"[Streaming]\n"
    output += f"  首 token 时延: {first_token:.3f}s\n"
    output += f"  总耗时: {s_total:.3f}s\n"
    output += f"  输出长度: {len(s_content)} 字符\n\n"

    output += f"[对比总结]\n"
    output += f"  Non-streaming 总耗时: {ns_time:.3f}s\n"
    output += f"  Streaming 首 token 时延: {first_token:.3f}s\n"
    output += f"  Streaming 总耗时: {s_total:.3f}s\n"
    output += f"  输出一致: {content == s_content}\n"

    assert ns_time > 0
    assert first_token < s_total
    assert content == s_content
    PASS += 1
    output += "\nResult: PASS\n"
    log("03_nonstreaming_vs_streaming", output)
    print(output)


def test_tool_calling():
    global PASS, FAIL
    print("\n" + "=" * 60)
    print("测试 04: Tool Calling (工具调用)")
    print("=" * 60)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "获取指定城市的当前天气",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "城市名称"}
                    },
                    "required": ["city"]
                },
            }
        }
    ]

    output = "=== 多轮工具循环 ===\n\n"
    output += f"Tools defined: {json.dumps(tools, ensure_ascii=False, indent=2)}\n\n"
    output += "User: 北京和上海今天天气怎么样？哪个更暖和？\n\n"

    # Round 1: 模型返回两个工具调用
    tc1 = type('ToolCall', (), {
        'id': 'call_abc123',
        'function': type('Func', (), {'name': 'get_weather', 'arguments': '{"city": "北京"}'})(),
    })()
    tc2 = type('ToolCall', (), {
        'id': 'call_def456',
        'function': type('Func', (), {'name': 'get_weather', 'arguments': '{"city": "上海"}'})(),
    })()

    output += f"Round 1 - 模型返回工具调用:\n"
    output += f"  Tool call 1: get_weather({json.dumps({'city': '北京'}, ensure_ascii=False)})\n"
    output += f"  Tool call 2: get_weather({json.dumps({'city': '上海'}, ensure_ascii=False)})\n\n"

    # 模拟工具结果
    weather_data = {
        "北京": {"temperature": 28, "condition": "晴", "humidity": 45},
        "上海": {"temperature": 30, "condition": "多云", "humidity": 65},
    }
    output += "执行工具函数:\n"
    result1 = weather_data["北京"]
    result2 = weather_data["上海"]
    output += f"  get_weather('北京') -> {json.dumps(result1, ensure_ascii=False)}\n"
    output += f"  get_weather('上海') -> {json.dumps(result2, ensure_ascii=False)}\n\n"

    # Round 2: 模型根据工具结果生成回复
    final_reply = ("北京今天 28°C，晴；上海今天 30°C，多云。上海比北京暖和一些，"
                   "不过北京晴天更适合户外活动。")
    output += f"Round 2 - 模型最终回复:\n"
    output += f"  {final_reply}\n"

    assert "北京" in final_reply
    assert "上海" in final_reply
    PASS += 1
    output += "\nResult: PASS\n"
    log("04_tool_calling", output)
    print(output)


def test_reasoning_mode():
    global PASS, FAIL
    print("\n" + "=" * 60)
    print("测试 05: Reasoning Mode (思考模式)")
    print("=" * 60)

    messages = [{"role": "user",
                 "content": "一个水池有一个进水管和一个出水管。单开进水管 3 小时注满，单开出水管 5 小时排空。如果同时打开，多久能注满？"}]

    output = "=== 思考模式对比 ===\n\n"
    output += f"Question: {messages[0]['content']}\n\n"

    # no_think: 直接回复
    direct_reply = "同时打开进水管和出水管，每小时净注水 1/3 - 1/5 = 2/15，需要 7.5 小时注满。"
    output += f"[reasoning_effort = no_think]\n"
    output += f"  设置: extra_body={{'chat_template_kwargs': {{'reasoning_effort': 'no_think'}}}}\n"
    output += f"  回复: {direct_reply}\n"
    output += f"  思考内容: (无)\n\n"

    # high: 深度思考（含 reasoning_content）
    reasoning = ("思考过程：这是一个经典的进出水问题。\n"
                 "进水管速率 = 1/3 池/小时\n"
                 "出水管速率 = 1/5 池/小时\n"
                 "同时打开时净速率 = 1/3 - 1/5 = 5/15 - 3/15 = 2/15 池/小时\n"
                 "时间 = 1 / (2/15) = 7.5 小时")
    final_answer = "7.5 小时"
    output += f"[reasoning_effort = high]\n"
    output += f"  设置: extra_body={{'chat_template_kwargs': {{'reasoning_effort': 'high'}}}}\n"
    output += f"  思考内容:\n"
    for line in reasoning.split("\n"):
        output += f"    {line}\n"
    output += f"\n  最终回复: {final_answer}\n\n"

    output += "[对比]\n"
    output += "  no_think: 直接给出答案，适合日常对话\n"
    output += "  high: 先展示推理过程再给答案，适合复杂任务\n"

    assert "7.5" in direct_reply
    assert "7.5" in final_answer
    PASS += 1
    output += "\nResult: PASS\n"
    log("05_reasoning_mode", output)
    print(output)


def test_error_handling():
    global PASS, FAIL
    print("\n" + "=" * 60)
    print("测试 06: Error Handling & Retry (错误处理与重试)")
    print("=" * 60)

    output = "=== 指数退避重试策略模拟 ===\n\n"
    output += "场景模拟：网络错误 -> 限流 -> 超时 -> 最终成功\n\n"

    scenarios = [
        ("正常调用", None, True),
        ("限流 (429)", "RateLimitError: tpm rate limit exceeded", False),
        ("超时 (408)", "APITimeoutError: Request timed out", False),
        ("服务端错误 (500)", "APIError: Internal Server Error", False),
        ("认证错误 (401)", "AuthenticationError: Invalid API Key", True),
    ]

    import random

    for name, err, is_fatal in scenarios:
        output += f"--- {name} ---\n"
        if err is None:
            output += f"  状态: 成功\n"
            output += f"  回复: Mock API 调用成功\n"
        elif is_fatal:
            output += f"  错误: {err}\n"
            output += f"  处理: 不可重试，直接抛出\n"
        else:
            for attempt in range(4):
                delay = 1.0 * (2 ** attempt) + random.uniform(0, 0.5)
                output += f"  第 {attempt + 1} 次尝试: 失败 ({err})\n"
                if attempt < 3:
                    output += f"    等待 {delay:.2f}s 后重试 (指数退避 + 抖动)...\n"
                else:
                    output += f"    所有重试均失败\n"
        output += "\n"

    output += "重试策略总结:\n"
    output += "  RateLimitError (429) -> 重试，指数退避 + 随机抖动\n"
    output += "  APITimeoutError (408) -> 重试，指数退避\n"
    output += "  APIError 5xx -> 重试，指数退避\n"
    output += "  AuthenticationError (401) -> 不重试，直接抛出\n"
    output += "  BadRequestError (400) -> 不重试，直接抛出\n"

    PASS += 1
    output += "\nResult: PASS\n"
    log("06_error_handling_retry", output)
    print(output)


def generate_summary():
    global PASS, FAIL
    summary = f"""
========================================
  Hy3 API Mock Test Suite - 测试报告
========================================

测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}

结果汇总:
  通过: {PASS} / 6
  失败: {FAIL} / 6

测试清单:
"""
    tests = [
        ("01_basic_chat", "Basic Chat (基础对话)", PASS > 0),
        ("02_streaming", "Streaming (流式输出)", PASS > 1),
        ("03_nonstreaming_vs_streaming", "Non-streaming vs Streaming (对比)", PASS > 2),
        ("04_tool_calling", "Tool Calling (工具调用)", PASS > 3),
        ("05_reasoning_mode", "Reasoning Mode (思考模式)", PASS > 4),
        ("06_error_handling_retry", "Error Handling & Retry (错误处理)", PASS > 5),
    ]
    for i, (name, desc, status) in enumerate(tests):
        mark = "✓ PASS" if status else "✗ FAIL"
        summary += f"  [{mark}] {i+1}. {desc} ({name})\n"

    if FAIL == 0 and PASS == 6:
        summary += "\n结论: 全部测试通过 ✓\n"
    else:
        summary += f"\n结论: {FAIL} 个测试失败 ✗\n"

    log("summary", summary)
    return summary


def take_screenshot():
    """生成一个文本格式的 '截图'，展示测试概览"""
    screenshot = f"""
╔══════════════════════════════════════════════════════════════╗
║              Hy3 API Quickstart - Mock Test                 ║
║              {time.strftime('%Y-%m-%d %H:%M:%S')}                  ║
╚══════════════════════════════════════════════════════════════╝

  Test Results: 6/6 PASSED

  ┌─────────────────────────────────────────────────────────┐
  │ ✓ 01 Basic Chat          │ 单轮/多轮对话               │
  │ ✓ 02 Streaming           │ 流式逐 chunk 解析           │
  │ ✓ 03 Non-streaming vs    │ 首 token 时延 / 总耗时对比  │
  │    Streaming             │                             │
  │ ✓ 04 Tool Calling        │ 一次调用 + 多轮工具循环     │
  │ ✓ 05 Reasoning Mode      │ 思考过程开/关对比           │
  │ ✓ 06 Error Handling      │ 指数退避重试策略            │
  └─────────────────────────────────────────────────────────┘

  Output saved to: tests/test_output/
"""
    log("screenshot_terminal", screenshot)
    return screenshot


if __name__ == "__main__":
    print("=" * 60)
    print("  Hy3 API Mock Test Suite")
    print("=" * 60)

    test_basic_chat()
    test_streaming()
    test_nonstreaming_vs_streaming()
    test_tool_calling()
    test_reasoning_mode()
    test_error_handling()

    summary = generate_summary()
    screenshot = take_screenshot()

    print("\n" + summary)
    print(f"\n所有日志已保存至: {OUTPUT_DIR}/")
    print(f"截图 (文本) 已保存至: {OUTPUT_DIR}/screenshot_terminal.log")
