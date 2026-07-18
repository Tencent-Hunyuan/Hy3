"""Optional live smoke tests against TokenHub or a local Hy3 server.

Skipped automatically unless HY3_LIVE=1 is set.

Usage:
  export HY3_LIVE=1
  export HY3_BASE_URL=https://tokenhub.tencentmaas.com/v1
  export HY3_API_KEY=...   # never commit
  export HY3_MODEL=hy3
  pytest examples/tests/test_live_smoke.py -q
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import (  # noqa: E402
    chat_completion,
    collect_stream,
    extract_reasoning_and_content,
    make_client,
    run_tool_loop,
)

LIVE = os.environ.get("HY3_LIVE", "").strip() in {"1", "true", "TRUE", "yes", "YES"}

pytestmark = pytest.mark.skipif(
    not LIVE,
    reason="Set HY3_LIVE=1 (and HY3_API_KEY / HY3_BASE_URL) to run live smokes",
)


@pytest.fixture(scope="module")
def client():
    # Hosted TokenHub needs a real key; local may use EMPTY.
    base = os.environ.get("HY3_BASE_URL", "")
    require_key = "tokenhub" in base.lower() or base.startswith("https://")
    return make_client(require_api_key=require_key)


def test_live_basic_chat(client):
    r = chat_completion(
        client,
        [{"role": "user", "content": "用一句话介绍你自己。"}],
        reasoning="no_think",
        max_tokens=128,
    )
    content = r.choices[0].message.content
    assert content and len(content) > 0
    assert r.usage is None or r.usage.total_tokens > 0


def test_live_streaming(client):
    stream = chat_completion(
        client,
        [{"role": "user", "content": "数到 3。"}],
        reasoning="no_think",
        max_tokens=64,
        stream=True,
    )
    text, ttft, total = collect_stream(stream)
    assert text
    assert total >= 0
    # TTFT may be very small on fast endpoints but should be set if any text arrived
    if text:
        assert ttft is not None


def test_live_reasoning_high(client):
    r = chat_completion(
        client,
        [{"role": "user", "content": "1+2+3等于几？只给答案。"}],
        reasoning="high",
        max_tokens=1024,
    )
    reasoning, content = extract_reasoning_and_content(r.choices[0].message)
    assert content
    # TokenHub should separate reasoning_content when thinking is enabled.
    # Local without parser may leave it empty — accept either but prefer present.
    if "tokenhub" in os.environ.get("HY3_BASE_URL", "").lower():
        assert reasoning, "expected reasoning_content on TokenHub with thinking enabled"


def test_live_tool_call(client):
    def get_weather(city: str) -> str:
        return f"{city}: mock-sunny"

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "查询城市天气",
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            },
        }
    ]
    messages = [{"role": "user", "content": "北京今天天气怎么样？"}]
    final = run_tool_loop(
        client,
        messages,
        tools,
        {"get_weather": get_weather},
        max_iterations=3,
        reasoning="no_think",
    )
    # Either tool path produced a final answer, or model answered directly.
    assert final is not None
    # If tools ran, history should contain a tool role message.
    # Not strictly required if model answers without tools.
    assert getattr(final, "content", None) or any(
        isinstance(m, dict) and m.get("role") == "tool" for m in messages
    )
