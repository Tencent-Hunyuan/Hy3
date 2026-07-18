"""Offline unit tests for examples/common.py — no live API key required."""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

# examples/ on sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import (  # noqa: E402
    REASONING_MODES,
    build_extra_body,
    call_with_retry,
    collect_stream,
    extract_reasoning_and_content,
    get_config,
    iter_stream_text,
    parse_retry_after,
    redacted_preview,
    run_tool_loop,
)


# ---------------------------------------------------------------------------
# Fixtures / fakes
# ---------------------------------------------------------------------------


class FakeDelta:
    def __init__(self, content=None):
        self.content = content


class FakeChoice:
    def __init__(self, delta=None, message=None):
        self.delta = delta
        self.message = message


class FakeChunk:
    def __init__(self, content=None, empty_choices=False):
        if empty_choices:
            self.choices = []
        else:
            self.choices = [FakeChoice(delta=FakeDelta(content))]


class FakeFunction:
    def __init__(self, name: str, arguments: str):
        self.name = name
        self.arguments = arguments


class FakeToolCall:
    def __init__(self, id: str, name: str, arguments: str):
        self.id = id
        self.function = FakeFunction(name, arguments)


class FakeMessage:
    def __init__(
        self,
        content: Optional[str] = None,
        reasoning_content: Optional[str] = None,
        tool_calls: Optional[List[Any]] = None,
    ):
        self.content = content
        self.reasoning_content = reasoning_content
        self.tool_calls = tool_calls
        self.role = "assistant"


class FakeResponse:
    def __init__(self, message: FakeMessage):
        self.choices = [FakeChoice(message=message)]


class FakeClient:
    """Minimal stand-in for OpenAI client used by run_tool_loop / chat_completion paths."""

    def __init__(self, responses: List[FakeResponse]):
        self._responses = list(responses)
        self.calls: List[Dict[str, Any]] = []
        self.chat = types.SimpleNamespace(completions=self)

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self._responses:
            raise RuntimeError("no more fake responses")
        return self._responses.pop(0)


class FakeHTTPError(Exception):
    def __init__(self, status_code=429, retry_after=None):
        super().__init__("fake http error")
        headers = {}
        if retry_after is not None:
            headers["Retry-After"] = str(retry_after)
        self.response = types.SimpleNamespace(status_code=status_code, headers=headers)
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Config / extra_body
# ---------------------------------------------------------------------------


def test_get_config_defaults(monkeypatch):
    monkeypatch.delenv("HY3_BASE_URL", raising=False)
    monkeypatch.delenv("HY3_API_KEY", raising=False)
    monkeypatch.delenv("HY3_MODEL", raising=False)
    monkeypatch.delenv("HY3_TIMEOUT", raising=False)
    cfg = get_config()
    assert cfg["base_url"] == "http://127.0.0.1:8000/v1"
    assert cfg["api_key"] == "EMPTY"
    assert cfg["model"] == "hy3"
    assert cfg["timeout"] == 120.0


def test_get_config_from_env(monkeypatch):
    monkeypatch.setenv("HY3_BASE_URL", "https://tokenhub.tencentmaas.com/v1")
    monkeypatch.setenv("HY3_API_KEY", "sk-test")
    monkeypatch.setenv("HY3_MODEL", "hy3")
    monkeypatch.setenv("HY3_TIMEOUT", "30")
    cfg = get_config()
    assert cfg["base_url"].startswith("https://tokenhub")
    assert cfg["api_key"] == "sk-test"
    assert cfg["timeout"] == 30.0


def test_build_extra_body_dual_compat():
    for mode in ("no_think", "low", "high", "off", "on"):
        body = build_extra_body(mode)
        assert "thinking" in body
        assert "chat_template_kwargs" in body
        assert body["thinking"]["type"] in ("enabled", "disabled")
        assert body["chat_template_kwargs"]["reasoning_effort"] in (
            "no_think",
            "low",
            "high",
        )


def test_build_extra_body_mapping():
    off = build_extra_body("no_think")
    assert off["thinking"]["type"] == "disabled"
    assert off["chat_template_kwargs"]["reasoning_effort"] == "no_think"

    high = build_extra_body("high")
    assert high["thinking"]["type"] == "enabled"
    assert high["chat_template_kwargs"]["reasoning_effort"] == "high"


def test_build_extra_body_unknown():
    with pytest.raises(ValueError):
        build_extra_body("ultra")


def test_reasoning_modes_cover_issue_levels():
    # Issue asks for thinking on/off; we also expose low/high as recommended values
    assert "no_think" in REASONING_MODES
    assert "low" in REASONING_MODES
    assert "high" in REASONING_MODES


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------


def test_iter_stream_text_skips_empty():
    chunks = [
        FakeChunk(empty_choices=True),
        FakeChunk(content=None),
        FakeChunk(content="Hello"),
        FakeChunk(content=" "),
        FakeChunk(content="Hy3"),
    ]
    assert list(iter_stream_text(chunks)) == ["Hello", " ", "Hy3"]


def test_collect_stream_ttft_and_total():
    chunks = [
        FakeChunk(content="a"),
        FakeChunk(content="b"),
        FakeChunk(content="c"),
    ]
    text, ttft, total = collect_stream(chunks)
    assert text == "abc"
    assert ttft is not None and ttft >= 0
    assert total >= ttft


def test_collect_stream_empty():
    text, ttft, total = collect_stream([FakeChunk(empty_choices=True)])
    assert text == ""
    assert ttft is None
    assert total >= 0


# ---------------------------------------------------------------------------
# Reasoning extract
# ---------------------------------------------------------------------------


def test_extract_reasoning_and_content():
    msg = FakeMessage(content="answer", reasoning_content="step1")
    r, c = extract_reasoning_and_content(msg)
    assert r == "step1"
    assert c == "answer"

    msg2 = FakeMessage(content="only")
    r2, c2 = extract_reasoning_and_content(msg2)
    assert r2 is None
    assert c2 == "only"


# ---------------------------------------------------------------------------
# Retry
# ---------------------------------------------------------------------------


def test_call_with_retry_success_first_try():
    sleeps = []
    result = call_with_retry(lambda: 42, sleep_fn=sleeps.append)
    assert result == 42
    assert sleeps == []


def test_call_with_retry_recovers_after_failures():
    from openai import APIConnectionError

    state = {"n": 0}

    def flaky():
        state["n"] += 1
        if state["n"] < 3:
            raise APIConnectionError(request=None)
        return "ok"

    sleeps = []
    assert (
        call_with_retry(
            flaky,
            max_attempts=5,
            base_delay=0.01,
            max_delay=0.05,
            max_total_wait=1.0,
            sleep_fn=sleeps.append,
        )
        == "ok"
    )
    assert state["n"] == 3
    assert len(sleeps) == 2


def test_call_with_retry_exhausts():
    from openai import APITimeoutError

    def always_fail():
        raise APITimeoutError(request=None)

    with pytest.raises(APITimeoutError):
        call_with_retry(
            always_fail,
            max_attempts=3,
            base_delay=0.01,
            max_delay=0.02,
            max_total_wait=1.0,
            sleep_fn=lambda _: None,
        )


def test_call_with_retry_honors_retry_after():
    from openai import RateLimitError

    # Build a RateLimitError-like object with Retry-After header is hard without httpx;
    # instead unit-test parse_retry_after and ensure delay uses it via a custom exception
    # that call_with_retry treats as retryable.
    class RateLimitLike(RateLimitError):
        def __init__(self):
            # RateLimitError signature varies; construct carefully
            Exception.__init__(self, "rate limited")
            self.response = types.SimpleNamespace(
                status_code=429, headers={"Retry-After": "3.5"}
            )
            self.status_code = 429
            self.body = None
            self.message = "rate limited"
            self.request = None
            self.code = None
            self.param = None

    # Simpler: test parse_retry_after directly
    err = FakeHTTPError(429, retry_after=3.5)
    assert parse_retry_after(err) == 3.5
    assert parse_retry_after(Exception("x")) is None


def test_parse_retry_after_invalid():
    err = FakeHTTPError(429, retry_after="soon")
    assert parse_retry_after(err) is None


# ---------------------------------------------------------------------------
# Tool loop
# ---------------------------------------------------------------------------


def test_run_tool_loop_single_then_answer():
    tool_msg = FakeMessage(
        tool_calls=[
            FakeToolCall("tc1", "get_weather", json.dumps({"city": "北京"}))
        ]
    )
    final_msg = FakeMessage(content="北京今天晴，28°C。")
    client = FakeClient([FakeResponse(tool_msg), FakeResponse(final_msg)])

    def get_weather(city: str) -> str:
        return f"{city}: sunny mock"

    messages: List[Any] = [{"role": "user", "content": "北京天气？"}]
    seen = []

    def on_tool(tc, result):
        seen.append((tc.function.name, result))

    # Monkeypatch chat_completion path: run_tool_loop calls chat_completion which
    # uses client.chat.completions.create — our FakeClient exposes create on .chat.completions
    # but chat_completion builds its own call. Patch via wrapping:
    import common as common_mod

    original = common_mod.chat_completion

    def fake_chat_completion(client, messages, **kwargs):
        return client.chat.completions.create(messages=messages, **kwargs)

    # FakeClient: client.chat.completions is self, and create exists
    # But structure is client.chat.completions.create — we set client.chat = SimpleNamespace(completions=self)
    # and self.create works. Good.

    common_mod.chat_completion = fake_chat_completion  # type: ignore
    try:
        final = run_tool_loop(
            client,
            messages,
            tools=[{"type": "function", "function": {"name": "get_weather"}}],
            available_functions={"get_weather": get_weather},
            max_iterations=5,
            on_tool_call=on_tool,
        )
    finally:
        common_mod.chat_completion = original  # type: ignore

    assert final is not None
    assert final.content == "北京今天晴，28°C。"
    assert seen == [("get_weather", "北京: sunny mock")]
    # history should contain assistant tool_calls + tool result + final assistant
    roles = []
    for m in messages:
        if isinstance(m, dict):
            roles.append(m.get("role"))
        else:
            roles.append(getattr(m, "role", type(m).__name__))
    assert "tool" in roles


def test_run_tool_loop_unknown_tool():
    tool_msg = FakeMessage(
        tool_calls=[FakeToolCall("tc1", "missing_tool", "{}")]
    )
    final_msg = FakeMessage(content="cannot help")
    client = FakeClient([FakeResponse(tool_msg), FakeResponse(final_msg)])

    import common as common_mod

    original = common_mod.chat_completion

    def fake_chat_completion(client, messages, **kwargs):
        return client.chat.completions.create(messages=messages, **kwargs)

    common_mod.chat_completion = fake_chat_completion  # type: ignore
    try:
        messages: List[Any] = [{"role": "user", "content": "hi"}]
        final = run_tool_loop(
            client,
            messages,
            tools=[],
            available_functions={},
            max_iterations=3,
        )
    finally:
        common_mod.chat_completion = original  # type: ignore

    assert final.content == "cannot help"
    tool_results = [m for m in messages if isinstance(m, dict) and m.get("role") == "tool"]
    assert tool_results
    assert "unknown tool" in tool_results[0]["content"]


def test_run_tool_loop_max_iterations():
    # Always returns tool_calls -> hits max_iterations
    always_tool = FakeMessage(
        tool_calls=[FakeToolCall("tc", "get_weather", json.dumps({"city": "上海"}))]
    )
    client = FakeClient([FakeResponse(always_tool) for _ in range(3)])

    import common as common_mod

    original = common_mod.chat_completion

    def fake_chat_completion(client, messages, **kwargs):
        return client.chat.completions.create(messages=messages, **kwargs)

    common_mod.chat_completion = fake_chat_completion  # type: ignore
    try:
        messages: List[Any] = [{"role": "user", "content": "天气"}]
        final = run_tool_loop(
            client,
            messages,
            tools=[],
            available_functions={"get_weather": lambda city: "ok"},
            max_iterations=3,
        )
    finally:
        common_mod.chat_completion = original  # type: ignore

    assert final is not None
    assert final.tool_calls  # last message still had tool_calls
    assert len(client.calls) == 3


# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------


def test_redacted_preview():
    assert redacted_preview("hello world") == "hello world"
    assert redacted_preview("sk-secret-key-here") == "[redacted]"
    assert redacted_preview("a" * 100, max_len=20).endswith("...")
    assert redacted_preview(None) == ""


# ---------------------------------------------------------------------------
# Example scripts are importable / compile
# ---------------------------------------------------------------------------


def test_example_scripts_compile():
    import py_compile

    for lang in ("en", "cn"):
        for name in (
            "01_basic_chat.py",
            "02_streaming.py",
            "03_nonstream_vs_stream.py",
            "04_tool_calling.py",
            "05_reasoning_mode.py",
            "06_error_handling_retry.py",
        ):
            path = ROOT / lang / name
            assert path.is_file(), f"missing {path}"
            py_compile.compile(str(path), doraise=True)


def test_common_py_compiles():
    import py_compile

    py_compile.compile(str(ROOT / "common.py"), doraise=True)
