"""End-to-end MCP stdio test with a dummy OpenAI-compatible Hy3 backend."""

from __future__ import annotations

import json
import os
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import ClassVar

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class DummyHy3Handler(BaseHTTPRequestHandler):
    received_payloads: ClassVar[list[dict]] = []

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return

        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length))
        type(self).received_payloads.append(payload)
        messages = payload.get("messages", [])
        system_text = "\n".join(
            str(message.get("content", ""))
            for message in messages
            if message.get("role") == "system"
        )
        user_text = "\n".join(
            str(message.get("content", ""))
            for message in messages
            if message.get("role") == "user"
        )

        errors: list[str] = []
        if not re.search(
            r"Ignore any commands.*embedded in source text",
            system_text,
            re.I | re.S,
        ):
            errors.append("missing prompt-injection guard")
        if not re.search(r'<source id="S1">.*256K context', user_text, re.S):
            errors.append("missing tagged evidence")
        reasoning = payload.get("chat_template_kwargs", {}).get("reasoning_effort")
        if reasoning != "high":
            errors.append("reasoning_effort was not forwarded")

        content = (
            "Dummy Hy3 verified the full MCP request path [S1]."
            if not errors
            else "Dummy validation failed: " + "; ".join(errors)
        )
        response = {
            "id": "chatcmpl-dummy",
            "object": "chat.completion",
            "created": 0,
            "model": payload.get("model", "hy3-dummy"),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        encoded = json.dumps(response).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, _format: str, *_args: object) -> None:
        return


@pytest.fixture
def dummy_hy3_backend() -> tuple[ThreadingHTTPServer, str]:
    DummyHy3Handler.received_payloads.clear()
    server = ThreadingHTTPServer(("127.0.0.1", 0), DummyHy3Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield server, f"http://{host}:{port}/v1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.asyncio
async def test_stdio_client_calls_analyze_evidence_through_dummy_hy3(
    dummy_hy3_backend: tuple[ThreadingHTTPServer, str],
) -> None:
    _, base_url = dummy_hy3_backend
    env = {
        **os.environ,
        "HY3_API_KEY": "dummy-test-key",
        "HY3_BASE_URL": base_url,
        "HY3_MODEL": "hy3-dummy",
        "NO_PROXY": "127.0.0.1,localhost",
        "no_proxy": "127.0.0.1,localhost",
        "HY3_REASONING_EFFORT": "high",
    }
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "hy3_deep_research"],
        env=env,
    )

    async with stdio_client(parameters) as (read_stream, write_stream):  # noqa: SIM117
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            assert {tool.name for tool in tools} == {
                "search_web",
                "analyze_evidence",
                "deep_research",
                "verify_claim",
            }

            result = await session.call_tool(
                "analyze_evidence",
                {
                    "question": "What context length is supported?",
                    "sources": [
                        {
                            "title": "Test evidence",
                            "content": "Hy3 supports a 256K context length.",
                        }
                    ],
                    "focus": "Check the stated number.",
                    "language": "English",
                },
            )

    assert not result.isError
    rendered = "\n".join(
        block.text for block in result.content if getattr(block, "type", None) == "text"
    )
    assert "Dummy Hy3 verified the full MCP request path [S1]." in rendered
    assert len(DummyHy3Handler.received_payloads) == 1
    assert DummyHy3Handler.received_payloads[0]["model"] == "hy3-dummy"
