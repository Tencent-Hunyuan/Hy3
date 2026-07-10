from __future__ import annotations

import unittest

from openai import OpenAI

from examples.api.tests.fake_server import FakeOpenAIServer


class FakeOpenAIServerTests(unittest.TestCase):
    def test_returns_queued_json_completion(self) -> None:
        completion = {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 0,
            "model": "hy3",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "pong"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
        }

        with FakeOpenAIServer() as server:
            server.enqueue_json(completion)
            client = OpenAI(
                base_url=server.base_url,
                api_key="EMPTY",
                max_retries=0,
            )

            response = client.chat.completions.create(
                model="hy3",
                messages=[{"role": "user", "content": "ping"}],
            )

        self.assertEqual(response.choices[0].message.content, "pong")
        self.assertEqual(server.requests[0]["json"]["model"], "hy3")

    def test_streams_queued_sse_completion_chunks(self) -> None:
        chunks = [
            {
                "id": "chatcmpl-test",
                "object": "chat.completion.chunk",
                "created": 0,
                "model": "hy3",
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": "Hello"},
                        "finish_reason": None,
                    }
                ],
            },
            {
                "id": "chatcmpl-test",
                "object": "chat.completion.chunk",
                "created": 0,
                "model": "hy3",
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": " world"},
                        "finish_reason": "stop",
                    }
                ],
            },
        ]

        with FakeOpenAIServer() as server:
            server.enqueue_sse(chunks)
            client = OpenAI(
                base_url=server.base_url,
                api_key="EMPTY",
                max_retries=0,
            )

            stream = client.chat.completions.create(
                model="hy3",
                messages=[{"role": "user", "content": "ping"}],
                stream=True,
            )
            content = "".join(
                chunk.choices[0].delta.content or "" for chunk in stream
            )

        self.assertEqual(content, "Hello world")

    def test_sse_headers_can_be_extended_and_overridden(self) -> None:
        server = FakeOpenAIServer()

        server.enqueue_sse(
            [],
            headers={"X-Test": "yes", "Cache-Control": "custom"},
        )

        response = server.responses[0]
        self.assertEqual(response.headers["Content-Type"], "text/event-stream")
        self.assertEqual(response.headers["X-Test"], "yes")
        self.assertEqual(response.headers["Cache-Control"], "custom")


if __name__ == "__main__":
    unittest.main()
