"""Offline protocol tests for all Hy3 API examples."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
from openai import OpenAI

API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

from common import assistant_message_dict  # noqa: E402


def load_example(filename: str) -> Any:
    module_name = f"hy3_example_{filename.removesuffix('.py')}"
    spec = importlib.util.spec_from_file_location(module_name, API_DIR / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


BASIC = load_example("01_basic_chat.py")
STREAMING = load_example("02_streaming.py")
LATENCY = load_example("03_latency_comparison.py")
TOOLS = load_example("04_tool_calling.py")
REASONING = load_example("05_reasoning_mode.py")
RETRY = load_example("06_error_handling_retry.py")


class Dumpable:
    def __init__(self, **values: Any) -> None:
        self.__dict__.update(values)

    def model_dump(self, **_: Any) -> dict[str, Any]:
        return {key: value for key, value in self.__dict__.items() if value is not None}


def usage() -> Dumpable:
    return Dumpable(prompt_tokens=10, completion_tokens=20, total_tokens=30)


def response(
    *,
    content: str | None = "ok",
    finish_reason: str = "stop",
    tool_calls: list[Any] | None = None,
    reasoning_content: str | None = None,
) -> Dumpable:
    message = Dumpable(
        role="assistant",
        content=content,
        tool_calls=tool_calls,
        reasoning_content=reasoning_content,
    )
    return Dumpable(
        id="chatcmpl-test",
        model="hy3",
        choices=[Dumpable(message=message, finish_reason=finish_reason)],
        usage=usage(),
    )


class FakeCompletions:
    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = list(outcomes)
        self.requests: list[dict[str, Any]] = []

    def create(self, **request: Any) -> Any:
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeClient:
    def __init__(self, outcomes: list[Any]) -> None:
        self.chat = SimpleNamespace(completions=FakeCompletions(outcomes))


class FakeStatusError(Exception):
    def __init__(
        self,
        status_code: int,
        *,
        retry_after: str | None = None,
    ) -> None:
        super().__init__(f"HTTP {status_code}")
        headers = {} if retry_after is None else {"Retry-After": retry_after}
        self.status_code = status_code
        self.request_id = "req-redacted"
        self.response = SimpleNamespace(headers=headers)


class BasicChatTests(unittest.TestCase):
    def test_complete_response_fields_are_parsed(self) -> None:
        details = BASIC.response_details(response(content="hello"))
        self.assertEqual(details["id"], "chatcmpl-test")
        self.assertEqual(details["model"], "hy3")
        self.assertEqual(details["content"], "hello")
        self.assertEqual(details["finish_reason"], "stop")
        self.assertEqual(details["usage"]["total_tokens"], 30)

    def test_empty_choices_are_rejected(self) -> None:
        broken = Dumpable(id="x", model="hy3", choices=[], usage=None)
        with self.assertRaisesRegex(RuntimeError, "no choices"):
            BASIC.response_details(broken)


class StreamingTests(unittest.TestCase):
    def test_content_reasoning_finish_and_usage_trailer(self) -> None:
        chunks = [
            Dumpable(
                id="chunk-id",
                model="hy3",
                choices=[
                    Dumpable(
                        delta=Dumpable(content=None, reasoning_content="think "),
                        finish_reason=None,
                    )
                ],
                usage=None,
            ),
            Dumpable(
                id="chunk-id",
                model="hy3",
                choices=[
                    Dumpable(
                        delta=Dumpable(content="hello ", reasoning_content=None),
                        finish_reason=None,
                    )
                ],
                usage=None,
            ),
            Dumpable(
                id="chunk-id",
                model="hy3",
                choices=[
                    Dumpable(
                        delta=Dumpable(content="world", reasoning_content=None),
                        finish_reason="stop",
                    )
                ],
                usage=None,
            ),
            Dumpable(id="chunk-id", model="hy3", choices=[], usage=usage()),
        ]
        parsed = STREAMING.consume_stream(chunks, emit=False)
        self.assertEqual(parsed["content"], "hello world")
        self.assertEqual(parsed["reasoning_content"], "think ")
        self.assertEqual(parsed["finish_reason"], "stop")
        self.assertEqual(parsed["usage"]["total_tokens"], 30)
        self.assertEqual(parsed["chunk_count"], 4)


class LatencyTests(unittest.TestCase):
    def test_streaming_parser_accepts_usage_only_trailer(self) -> None:
        stream = [
            Dumpable(
                choices=[
                    Dumpable(
                        delta=Dumpable(content="answer", reasoning_content=None),
                        finish_reason="stop",
                    )
                ],
                usage=None,
            ),
            Dumpable(choices=[], usage=usage()),
        ]
        client = FakeClient([stream])
        result = LATENCY.run_streaming(client, {"model": "hy3", "messages": []})
        self.assertEqual(result["content"], "answer")
        self.assertEqual(result["finish_reason"], "stop")
        self.assertEqual(result["usage"]["total_tokens"], 30)
        self.assertIsNotNone(result["first_visible_chunk_seconds"])


class ToolCallingTests(unittest.TestCase):
    def make_tool_call(self, call_id: str, city: str) -> Dumpable:
        return Dumpable(
            id=call_id,
            type="function",
            function=Dumpable(
                name="get_weather",
                arguments=f'{{"city": "{city}"}}',
            ),
        )

    def test_allowlisted_tool_execution(self) -> None:
        result = TOOLS.execute_tool_call(self.make_tool_call("call-1", "北京"))
        self.assertIn('"temperature_c": 28', result)

    def test_invalid_json_becomes_tool_error(self) -> None:
        tool_call = Dumpable(
            id="call-bad",
            function=Dumpable(name="get_weather", arguments="not-json"),
        )
        result = TOOLS.execute_tool_call(tool_call)
        self.assertIn("error", result)

    def test_parallel_calls_are_replayed_before_final_answer(self) -> None:
        first = response(
            content=None,
            finish_reason="tool_calls",
            tool_calls=[
                self.make_tool_call("call-1", "北京"),
                self.make_tool_call("call-2", "上海"),
            ],
        )
        final = response(content="上海更暖和")
        client = FakeClient([first, final])
        messages = [{"role": "user", "content": "比较天气"}]
        answer = TOOLS.run_tool_loop(client, "hy3", messages)

        self.assertEqual(answer, "上海更暖和")
        self.assertEqual(len(client.chat.completions.requests), 2)
        second_request_messages = client.chat.completions.requests[1]["messages"]
        self.assertEqual(second_request_messages[-2]["tool_call_id"], "call-1")
        self.assertEqual(second_request_messages[-1]["tool_call_id"], "call-2")

    def test_assistant_history_preserves_reasoning(self) -> None:
        message = (
            response(
                content=None,
                finish_reason="tool_calls",
                tool_calls=[self.make_tool_call("call-1", "北京")],
                reasoning_content="need weather",
            )
            .choices[0]
            .message
        )
        serialized = assistant_message_dict(message)
        self.assertEqual(serialized["reasoning_content"], "need weather")
        self.assertEqual(serialized["tool_calls"][0]["id"], "call-1")


class ReasoningTests(unittest.TestCase):
    def test_provider_fields_are_sent_and_parsed(self) -> None:
        client = FakeClient([response(content="42", reasoning_content="6 * 7")])
        result = REASONING.call_reasoning_mode(
            client,
            "hy3",
            "calculate",
            enabled=True,
            effort="high",
        )
        request = client.chat.completions.requests[0]
        self.assertEqual(request["extra_body"]["thinking"]["type"], "enabled")
        self.assertEqual(request["extra_body"]["reasoning_effort"], "high")
        self.assertEqual(result["reasoning_content"], "6 * 7")
        self.assertEqual(result["content"], "42")

    def test_sdk_wire_payload_preserves_tokenhub_extensions(self) -> None:
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "id": "chatcmpl-wire-test",
                    "object": "chat.completion",
                    "created": 0,
                    "model": "hy3",
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": "done"},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 1,
                        "completion_tokens": 1,
                        "total_tokens": 2,
                    },
                },
            )

        http_client = httpx.Client(transport=httpx.MockTransport(handler))
        self.addCleanup(http_client.close)
        client = OpenAI(
            api_key="test-key",
            base_url="https://example.test/v1",
            http_client=http_client,
        )
        client.chat.completions.create(
            model="hy3",
            messages=[
                {"role": "user", "content": "use a tool"},
                {
                    "role": "assistant",
                    "content": None,
                    "reasoning_content": "need data",
                    "tool_calls": [],
                },
            ],
            extra_body={
                "thinking": {"type": "enabled"},
                "reasoning_effort": "high",
            },
        )

        body = captured["body"]
        self.assertEqual(body["thinking"], {"type": "enabled"})
        self.assertEqual(body["reasoning_effort"], "high")
        self.assertEqual(body["messages"][1]["reasoning_content"], "need data")


class RetryTests(unittest.TestCase):
    def test_retry_after_seconds_is_honored(self) -> None:
        error = FakeStatusError(429, retry_after="2")
        client = FakeClient([error, response(content="success")])
        sleeps: list[float] = []
        result = RETRY.request_with_retry(
            client,
            {"model": "hy3", "messages": []},
            sleep=sleeps.append,
            random_value=lambda: 0.0,
        )
        self.assertEqual(result.choices[0].message.content, "success")
        self.assertEqual(sleeps, [2.0])

    def test_retry_after_http_date(self) -> None:
        now = datetime(2026, 7, 18, tzinfo=timezone.utc)
        retry_at = format_datetime(now + timedelta(seconds=12), usegmt=True)
        error = FakeStatusError(429, retry_after=retry_at)
        self.assertEqual(RETRY.retry_after_seconds(error, now=now), 12.0)

    def test_non_retryable_status_is_not_retried(self) -> None:
        client = FakeClient([FakeStatusError(401)])
        sleeps: list[float] = []
        with self.assertRaises(FakeStatusError):
            RETRY.request_with_retry(
                client,
                {"model": "hy3", "messages": []},
                sleep=sleeps.append,
            )
        self.assertEqual(sleeps, [])
        self.assertEqual(len(client.chat.completions.requests), 1)

    def test_backoff_has_bounded_jitter(self) -> None:
        delay = RETRY.backoff_seconds(
            3,
            retry_after=None,
            base_delay=1.0,
            max_delay=30.0,
            random_value=1.0,
        )
        self.assertEqual(delay, 5.0)


if __name__ == "__main__":
    unittest.main()
