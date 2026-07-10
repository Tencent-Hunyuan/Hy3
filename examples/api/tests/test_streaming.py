from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock


API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

from common import StreamAccumulator
from tests.helpers import load_example


class StreamingExampleTests(unittest.TestCase):
    def test_prints_only_content_live_and_keeps_reasoning_separate(self) -> None:
        chunks = [
            SimpleNamespace(choices=[], usage=None),
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(reasoning_content="plan "),
                        finish_reason=None,
                    )
                ],
                usage=None,
            ),
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(content="Hello"),
                        finish_reason=None,
                    )
                ],
                usage=None,
            ),
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(content=" world"),
                        finish_reason="stop",
                    )
                ],
                usage=None,
            ),
            SimpleNamespace(choices=[], usage={"total_tokens": 7}),
        ]
        example = load_example("02_streaming.py")
        output = io.StringIO()

        with redirect_stdout(output):
            result = example.consume_stream(chunks)

        self.assertEqual(result.content, "Hello world")
        self.assertEqual(result.reasoning, "plan ")
        self.assertEqual(result.finish_reason, "stop")
        self.assertEqual(result.usage, {"total_tokens": 7})
        self.assertIn("Content: Hello world", output.getvalue())
        self.assertNotIn("Content: plan", output.getvalue())


class LatencyExampleTests(unittest.TestCase):
    def test_distinguishes_first_output_from_first_content(self) -> None:
        example = load_example("03_streaming_vs_non_streaming.py")
        chunks = [
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(
                            content=None,
                            reasoning="thinking",
                            model_extra={},
                            tool_calls=None,
                        ),
                        finish_reason=None,
                    )
                ],
                usage=None,
            ),
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(
                            content="answer",
                            reasoning=None,
                            model_extra={},
                            tool_calls=None,
                        ),
                        finish_reason=None,
                    )
                ],
                usage=None,
            ),
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(
                            content=None,
                            reasoning=None,
                            model_extra={},
                            tool_calls=None,
                        ),
                        finish_reason="stop",
                    )
                ],
                usage=None,
            ),
        ]
        client = MagicMock()
        client.chat.completions.create.return_value = iter(chunks)
        clock = iter([10.0, 10.1, 10.4, 11.0]).__next__
        request = {
            "model": "hy3",
            "messages": [{"role": "user", "content": "test"}],
            "temperature": 0.9,
            "top_p": 1.0,
            "max_tokens": 256,
            "extra_body": {
                "chat_template_kwargs": {"reasoning_effort": "no_think"}
            },
        }

        timing = example.measure_streaming(client, request, clock=clock)

        self.assertAlmostEqual(timing.first_output_seconds, 0.1)
        self.assertAlmostEqual(timing.first_content_seconds, 0.4)
        self.assertAlmostEqual(timing.total_seconds, 1.0)
        client.chat.completions.create.assert_called_once_with(
            **request,
            stream=True,
            stream_options={"include_usage": True},
        )

    def test_non_streaming_reports_total_latency_without_changing_request(self) -> None:
        example = load_example("03_streaming_vs_non_streaming.py")
        client = MagicMock()
        request = {
            "model": "hy3",
            "messages": [{"role": "user", "content": "test"}],
            "temperature": 0.9,
            "top_p": 1.0,
            "max_tokens": 256,
            "extra_body": {
                "chat_template_kwargs": {"reasoning_effort": "no_think"}
            },
        }
        clock = iter([20.0, 20.75]).__next__

        timing = example.measure_non_streaming(client, request, clock=clock)

        self.assertAlmostEqual(timing.total_seconds, 0.75)
        self.assertEqual(client.chat.completions.create.call_args.kwargs, request)


class StreamAccumulatorTests(unittest.TestCase):
    def test_accumulates_interleaved_streaming_response(self) -> None:
        chunks = [
            SimpleNamespace(choices=[], usage=None),
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(
                            content="Hello",
                            reasoning_content="plan ",
                            tool_calls=[
                                SimpleNamespace(
                                    index=0,
                                    id="call_",
                                    type="function",
                                    function=SimpleNamespace(
                                        name="get_",
                                        arguments='{"city":"Shen',
                                    ),
                                ),
                                SimpleNamespace(
                                    index=1,
                                    id="call_",
                                    type="function",
                                    function=SimpleNamespace(
                                        name="get_",
                                        arguments='{"timezone":"Asia/',
                                    ),
                                ),
                            ],
                        ),
                        finish_reason=None,
                    )
                ],
                usage=None,
            ),
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(
                            content=" world",
                            reasoning_content="carefully",
                            tool_calls=[
                                SimpleNamespace(
                                    index=1,
                                    id="time",
                                    type=None,
                                    function=SimpleNamespace(
                                        name="time",
                                        arguments='Hong_Kong"}',
                                    ),
                                ),
                                SimpleNamespace(
                                    index=0,
                                    id="weather",
                                    type=None,
                                    function=SimpleNamespace(
                                        name="weather",
                                        arguments='zhen"}',
                                    ),
                                ),
                            ],
                        ),
                        finish_reason="tool_calls",
                    )
                ],
                usage=None,
            ),
            SimpleNamespace(
                choices=[],
                usage=SimpleNamespace(
                    prompt_tokens=4,
                    completion_tokens=8,
                    total_tokens=12,
                ),
            ),
        ]
        accumulator = StreamAccumulator()

        for chunk in chunks:
            accumulator.add_chunk(chunk)

        result = accumulator.result()

        self.assertEqual(result.content, "Hello world")
        self.assertEqual(result.reasoning, "plan carefully")
        self.assertEqual(result.finish_reason, "tool_calls")
        self.assertEqual(result.usage["total_tokens"], 12)
        self.assertEqual(
            result.tool_calls,
            [
                {
                    "id": "call_weather",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": '{"city":"Shenzhen"}',
                    },
                },
                {
                    "id": "call_time",
                    "type": "function",
                    "function": {
                        "name": "get_time",
                        "arguments": '{"timezone":"Asia/Hong_Kong"}',
                    },
                },
            ],
        )

    def test_result_snapshots_do_not_share_nested_state(self) -> None:
        accumulator = StreamAccumulator()
        accumulator.add_chunk(
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(
                            reasoning_details=[
                                {
                                    "type": "reasoning.text",
                                    "text": "original",
                                    "metadata": {"steps": ["one"]},
                                }
                            ]
                        ),
                        finish_reason=None,
                    )
                ],
                usage={
                    "prompt_tokens": 4,
                    "completion_tokens": 8,
                    "total_tokens": 12,
                    "details": {"cached_tokens": 2},
                },
            )
        )

        earlier = accumulator.result()
        first = accumulator.result()
        first.usage["total_tokens"] = 99
        first.usage["details"]["cached_tokens"] = 99
        first.reasoning_details[0]["text"] = "changed"
        first.reasoning_details[0]["metadata"]["steps"].append("changed")

        second = accumulator.result()

        for snapshot in (earlier, second):
            self.assertEqual(snapshot.usage["total_tokens"], 12)
            self.assertEqual(snapshot.usage["details"]["cached_tokens"], 2)
            self.assertEqual(snapshot.reasoning_details[0]["text"], "original")
            self.assertEqual(
                snapshot.reasoning_details[0]["metadata"]["steps"],
                ["one"],
            )


if __name__ == "__main__":
    unittest.main()
