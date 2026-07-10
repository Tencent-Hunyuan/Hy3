from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace


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
