from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

from common import StreamAccumulator


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


if __name__ == "__main__":
    unittest.main()
