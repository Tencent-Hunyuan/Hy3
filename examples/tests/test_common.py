"""Offline unit tests for examples/common.py — no live API key required."""

from __future__ import annotations

import json
import random
import sys
import types
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

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
    redact_data,
    redact_text,
    redacted_preview,
    run_tool_loop,
    validate_config,
)


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


def test_validate_config_rejects_remote_http():
    with pytest.raises(ValueError, match="HTTPS"):
        validate_config(
            {
                "base_url": "http://example.com/v1",
                "api_key": "sk-x",
                "model": "hy3",
                "timeout": 10,
            }
        )


def test_validate_config_allows_local_http():
    cfg = validate_config(
        {
            "base_url": "http://127.0.0.1:8000/v1",
            "api_key": "EMPTY",
            "model": "hy3",
            "timeout": 10,
        }
    )
    assert cfg["base_url"].endswith("/v1")


def test_validate_config_require_api_key():
    with pytest.raises(ValueError, match="HY3_API_KEY"):
        validate_config(
            {
                "base_url": "https://tokenhub.tencentmaas.com/v1",
                "api_key": "EMPTY",
                "model": "hy3",
                "timeout": 10,
            },
            require_api_key=True,
        )


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
    assert "no_think" in REASONING_MODES
    assert "low" in REASONING_MODES
    assert "high" in REASONING_MODES


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


def test_extract_reasoning_and_content():
    msg = FakeMessage(content="answer", reasoning_content="step1")
    r, c = extract_reasoning_and_content(msg)
    assert r == "step1"
    assert c == "answer"

    msg2 = FakeMessage(content="only")
    r2, c2 = extract_reasoning_and_content(msg2)
    assert r2 is None
    assert c2 == "only"


def test_call_with_retry_success_first_try():
    sleeps = []
    result = call_with_retry(lambda: 42, sleep_fn=sleeps.append, jitter=0)
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
            jitter=0,
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
            jitter=0,
        )


def test_call_with_retry_jitter_deterministic():
    from openai import APIConnectionError

    state = {"n": 0}

    def flaky():
        state["n"] += 1
        if state["n"] < 2:
            raise APIConnectionError(request=None)
        return "ok"

    sleeps = []
    call_with_retry(
        flaky,
        max_attempts=3,
        base_delay=1.0,
        max_delay=10.0,
        max_total_wait=60.0,
        jitter=0.5,
        sleep_fn=sleeps.append,
        rng=random.Random(0),
    )
    assert len(sleeps) == 1
    # With seed 0 and jitter 0.5, delay is in [0.5, 1.0]
    assert 0.5 <= sleeps[0] <= 1.0


def test_parse_retry_after_numeric():
    err = FakeHTTPError(429, retry_after=3.5)
    assert parse_retry_after(err) == 3.5
    assert parse_retry_after(Exception("x")) is None


def test_parse_retry_after_invalid():
    err = FakeHTTPError(429, retry_after="soon")
    assert parse_retry_after(err) is None


def test_run_tool_loop_single_then_answer():
    tool_msg = FakeMessage(
        tool_calls=[FakeToolCall("tc1", "get_weather", json.dumps({"city": "北京"}))]
    )
    final_msg = FakeMessage(content="北京今天晴，28°C。")
    client = FakeClient([FakeResponse(tool_msg), FakeResponse(final_msg)])

    def get_weather(city: str) -> str:
        return f"{city}: sunny mock"

    messages: List[Any] = [{"role": "user", "content": "北京天气？"}]
    seen = []

    def on_tool(tc, result):
        seen.append((tc.function.name, result))

    import common as common_mod

    original = common_mod.chat_completion

    def fake_chat_completion(client, messages, **kwargs):
        return client.chat.completions.create(messages=messages, **kwargs)

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
    roles = []
    for m in messages:
        if isinstance(m, dict):
            roles.append(m.get("role"))
        else:
            roles.append(getattr(m, "role", type(m).__name__))
    assert "tool" in roles


def test_run_tool_loop_unknown_tool():
    tool_msg = FakeMessage(tool_calls=[FakeToolCall("tc1", "missing_tool", "{}")])
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
    assert final.tool_calls
    assert len(client.calls) == 3


def test_redacted_preview():
    assert redacted_preview("hello world") == "hello world"
    assert "redacted" in redacted_preview("sk-secretkeyvaluehere")
    assert redacted_preview("a" * 100, max_len=20).endswith("...")
    assert redacted_preview(None) == ""


def test_redact_text_bearer():
    s = redact_text("Authorization: Bearer abcdEFGH1234_+/=")
    assert "Bearer [redacted]" in s
    assert "abcdEFGH" not in s


def test_redact_data_nested():
    data = {
        "api_key": "sk-should-hide",
        "nested": {"authorization": "Bearer xyz", "ok": "value"},
        "items": ["sk-abcdefghi", "plain"],
    }
    out = redact_data(data)
    assert out["api_key"] == "[redacted]"
    assert out["nested"]["authorization"] == "[redacted]"
    assert out["nested"]["ok"] == "value"
    assert "redacted" in out["items"][0]
    assert out["items"][1] == "plain"


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
