from __future__ import annotations

import http.client
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from openai import OpenAI

from examples.api.tests import helpers
from examples.api.tests.fake_server import FakeOpenAIServer, _Handler


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
            with OpenAI(
                base_url=server.base_url,
                api_key="EMPTY",
                max_retries=0,
            ) as client:
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
            with OpenAI(
                base_url=server.base_url,
                api_key="EMPTY",
                max_retries=0,
            ) as client:
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

    def test_framing_headers_are_computed_by_the_server(self) -> None:
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
        }

        with FakeOpenAIServer() as server:
            server.enqueue_json(
                completion,
                headers={
                    "cOnTeNt-LeNgTh": "999",
                    "tRaNsFeR-EnCoDiNg": "chunked",
                    "X-Test": "yes",
                },
            )
            queued_headers = server.responses[0].headers
            lowered_names = {name.lower() for name in queued_headers}
            self.assertNotIn("content-length", lowered_names)
            self.assertNotIn("transfer-encoding", lowered_names)
            self.assertEqual(queued_headers["X-Test"], "yes")

            with OpenAI(
                base_url=server.base_url,
                api_key="EMPTY",
                max_retries=0,
                timeout=2,
            ) as client:
                response = client.chat.completions.create(
                    model="hy3",
                    messages=[{"role": "user", "content": "ping"}],
                )

        self.assertEqual(response.choices[0].message.content, "pong")

    def test_context_exit_closes_the_handler_connection(self) -> None:
        server = FakeOpenAIServer()
        handler_threads: list[threading.Thread] = []
        connection: http.client.HTTPConnection | None = None
        server_exited = False
        original_setup = _Handler.setup

        def capture_handler_thread(handler: _Handler) -> None:
            original_setup(handler)
            if handler.server is server.server:
                handler_threads.append(threading.current_thread())

        with patch.object(_Handler, "setup", capture_handler_thread):
            server.__enter__()
            try:
                server.enqueue_json({"ok": True})
                self.assertIsNotNone(server.server)
                assert server.server is not None
                host, port = server.server.server_address
                connection = http.client.HTTPConnection(host, port, timeout=2)
                connection.request(
                    "POST",
                    "/v1/chat/completions",
                    body=json.dumps({"model": "hy3"}),
                    headers={"Content-Type": "application/json"},
                )
                response = connection.getresponse()
                response.read()
                connection_header = response.getheader("Connection")
                server.__exit__(None, None, None)
                server_exited = True
                self.assertEqual(len(handler_threads), 1)
                handler_was_alive_after_exit = handler_threads[0].is_alive()
            finally:
                if connection is not None:
                    connection.close()
                if not server_exited:
                    server.__exit__(None, None, None)
                for handler_thread in handler_threads:
                    handler_thread.join(timeout=5)

        self.assertFalse(handler_was_alive_after_exit)
        self.assertEqual(connection_header, "close")
        self.assertFalse(handler_threads[0].is_alive())

    def test_error_response_closes_the_connection(self) -> None:
        with FakeOpenAIServer() as server:
            self.assertIsNotNone(server.server)
            assert server.server is not None
            host, port = server.server.server_address
            connection = http.client.HTTPConnection(host, port, timeout=2)
            try:
                connection.request(
                    "POST",
                    "/v1/chat/completions",
                    body=b"not-json",
                    headers={"Content-Type": "application/json"},
                )
                response = connection.getresponse()
                response.read()
                connection_header = response.getheader("Connection")
            finally:
                connection.close()

            self.assertEqual(connection_header, "close")


class ExampleHelperTests(unittest.TestCase):
    def test_load_example_restores_previous_module_after_failure(self) -> None:
        filename = "failure_existing.py"
        module_name = "hy3_example_failure_existing"
        original_module = sys.modules.get(module_name)
        previous_module = ModuleType(module_name)
        sys.modules[module_name] = previous_module

        try:
            with tempfile.TemporaryDirectory() as directory:
                api_dir = Path(directory)
                (api_dir / filename).write_text(
                    "raise ValueError('boom')\n",
                    encoding="utf-8",
                )
                with patch.object(helpers, "API_DIR", api_dir):
                    with self.assertRaises(RuntimeError) as captured:
                        helpers.load_example(filename)

            self.assertIs(sys.modules[module_name], previous_module)
            self.assertIsInstance(captured.exception.__cause__, ValueError)
        finally:
            if original_module is None:
                sys.modules.pop(module_name, None)
            else:
                sys.modules[module_name] = original_module

    def test_load_example_removes_new_module_after_failure(self) -> None:
        filename = "failure_new.py"
        module_name = "hy3_example_failure_new"
        original_module = sys.modules.pop(module_name, None)

        try:
            with tempfile.TemporaryDirectory() as directory:
                api_dir = Path(directory)
                (api_dir / filename).write_text(
                    "raise LookupError('boom')\n",
                    encoding="utf-8",
                )
                with patch.object(helpers, "API_DIR", api_dir):
                    with self.assertRaises(RuntimeError) as captured:
                        helpers.load_example(filename)

            self.assertIsNone(sys.modules.get(module_name))
            self.assertIsInstance(captured.exception.__cause__, LookupError)
        finally:
            sys.modules.pop(module_name, None)
            if original_module is not None:
                sys.modules[module_name] = original_module

    def test_load_example_keeps_successful_module(self) -> None:
        filename = "success.py"
        module_name = "hy3_example_success"
        original_module = sys.modules.pop(module_name, None)

        try:
            with tempfile.TemporaryDirectory() as directory:
                api_dir = Path(directory)
                (api_dir / filename).write_text("VALUE = 7\n", encoding="utf-8")
                with patch.object(helpers, "API_DIR", api_dir):
                    module = helpers.load_example(filename)

            self.assertEqual(module.VALUE, 7)
            self.assertIs(sys.modules[module_name], module)
        finally:
            sys.modules.pop(module_name, None)
            if original_module is not None:
                sys.modules[module_name] = original_module


if __name__ == "__main__":
    unittest.main()
