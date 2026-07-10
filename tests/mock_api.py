"""
Mock API 模块：模拟 Hy3 API 的响应格式
用于离线测试，无需真实 API Key
"""

import time
import json
import random


class MockChoice:
    def __init__(self, content, finish_reason="stop", tool_calls=None, reasoning_content=None):
        self.index = 0
        self.message = MockMessage(content, tool_calls, reasoning_content)
        self.delta = MockMessage(content, tool_calls, reasoning_content)
        self.finish_reason = finish_reason


class MockMessage:
    def __init__(self, content, tool_calls=None, reasoning_content=None):
        self.role = "assistant"
        self.content = content
        self.tool_calls = tool_calls
        self.reasoning_content = reasoning_content


class MockUsage:
    def __init__(self, prompt_tokens, completion_tokens):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = prompt_tokens + completion_tokens

    def __repr__(self):
        return f"Usage(prompt_tokens={self.prompt_tokens}, completion_tokens={self.completion_tokens}, total_tokens={self.total_tokens})"


class MockChunk:
    def __init__(self, content, finish_reason=None, usage=None):
        self.id = f"chatcmpl-mock-{random.randint(100000, 999999)}"
        self.object = "chat.completion.chunk"
        self.created = int(time.time())
        self.model = "hy3"
        if content is None and finish_reason:
            self.choices = [MockChoiceContent(None, finish_reason)]
        else:
            self.choices = [MockChoiceContent(content)]
        self.usage = usage


class MockChoiceContent:
    def __init__(self, content, finish_reason=None):
        self.index = 0
        self.delta = MockDelta(content)
        self.finish_reason = finish_reason


class MockDelta:
    def __init__(self, content):
        self.content = content
        self.role = "assistant" if content else None


class MockResponse:
    def __init__(self, content, tool_calls=None, reasoning_content=None,
                 prompt_tokens=50, completion_tokens=100):
        self.id = f"chatcmpl-mock-{random.randint(100000, 999999)}"
        self.object = "chat.completion"
        self.created = int(time.time())
        self.model = "hy3"
        self.choices = [MockChoice(content, tool_calls=tool_calls,
                                   reasoning_content=reasoning_content)]
        self.usage = MockUsage(prompt_tokens, completion_tokens)


def simulate_stream(content, chunk_size=5, delay=0.02):
    """模拟流式输出，逐 chunk 返回（字符级，保证精确重建）"""
    chars = list(content)
    i = 0
    while i < len(chars):
        piece = "".join(chars[i:i + chunk_size])
        yield MockChunk(piece)
        time.sleep(delay)
        i += chunk_size
    yield MockChunk(None, finish_reason="stop")


def simulate_stream_with_usage(content):
    """模拟流式输出并附带 usage 信息"""
    chunks = list(simulate_stream(content))
    for chunk in chunks[:-1]:
        yield chunk
    last = chunks[-1]
    last.usage = MockUsage(45, 120)
    yield last
