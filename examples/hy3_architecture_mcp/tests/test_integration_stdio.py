"""End-to-end integration test: real MCP stdio server + mock Hy3 HTTP endpoint.

Spins up a tiny OpenAI-compatible HTTP server returning a canned chat
completion, launches the actual MCP server as a subprocess, and drives a
real tool call through the official MCP client SDK. This verifies the full
wiring that unit tests cannot: stdio framing -> tool dispatch -> Hy3Client
HTTP call -> structured output returned to the client.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

CANONICAL_RESPONSE = {
    "understood_goals": ["Build a REST API for todo management"],
    "ambiguities": ["Auth model unspecified", "Persistence backend unclear"],
    "missing_information": ["Expected request volume", "Multi-tenancy?"],
    "clarifying_questions": [
        "Which authentication scheme (OAuth2 / session / API key)?",
        "PostgreSQL, MySQL, or something else for storage?",
    ],
    "acceptance_criteria": ["CRUD endpoints respond < 200ms at p99"],
    "assumptions": ["Single tenant unless stated otherwise"],
}


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _Handler(BaseHTTPRequestHandler):
    """Mock vLLM/OpenAI chat-completions endpoint."""

    def do_POST(self) -> None:  # noqa: N802 - stdlib naming
        length = int(self.headers.get("content-length", "0"))
        self.rfile.read(length)  # drain body
        content = json.dumps(CANONICAL_RESPONSE)
        payload = {
            "id": "chatcmpl-mock",
            "object": "chat.completion",
            "model": "hy3",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # silence noisy stderr
        pass


@pytest.fixture()
def mock_hy3():
    """Start a thread-local mock Hy3 endpoint; yield its base URL."""
    port = _free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}/v1"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


async def test_stdio_end_to_end_tool_call(mock_hy3, tmp_path):
    """clarify_requirements returns structured output through the stdio transport."""
    env = {
        **os.environ,
        "HY3_BASE_URL": mock_hy3,
        "HY3_API_KEY": "test-key-not-secret",
        "HY3_MODEL": "hy3",
        "HY3_REASONING_EFFORT": "no_think",
        "HY3_TIMEOUT_SECONDS": "10",
        "HY3_MAX_RETRIES": "0",
        "HY3_WORKSPACE_ROOT": str(tmp_path),
    }
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "hy3_architecture_mcp"],
        env=env,
    )
    async with (
        stdio_client(params) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()

        result = await session.call_tool(
            "clarify_requirements",
            {
                "requirement": "I want to build a todo app backend",
                "max_questions": 3,
            },
        )

    # The tool returns a structured dict; MCP wraps it as content blocks.
    assert not result.isError, f"tool reported error: {result.content}"
    # Reassemble the text content and parse the JSON payload.
    text = "".join(block.text for block in result.content if getattr(block, "type", "") == "text")
    data = json.loads(text)
    assert data["understood_goals"] == CANONICAL_RESPONSE["understood_goals"]
    assert data["clarifying_questions"] == CANONICAL_RESPONSE["clarifying_questions"]
    assert data["acceptance_criteria"] == CANONICAL_RESPONSE["acceptance_criteria"]
    assert data["assumptions"] == CANONICAL_RESPONSE["assumptions"]


async def test_stdio_workspace_guard_blocks_outside_path(mock_hy3, tmp_path):
    """analyze_project_context refuses a path outside HY3_WORKSPACE_ROOT."""
    env = {
        **os.environ,
        "HY3_BASE_URL": mock_hy3,
        "HY3_API_KEY": "test-key-not-secret",
        "HY3_MODEL": "hy3",
        "HY3_REASONING_EFFORT": "no_think",
        "HY3_TIMEOUT_SECONDS": "10",
        "HY3_MAX_RETRIES": "0",
        "HY3_WORKSPACE_ROOT": str(tmp_path),
    }
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "hy3_architecture_mcp"],
        env=env,
    )
    async with (
        stdio_client(params) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()

        # An absolute path outside the workspace must be refused before
        # the Hy3 endpoint is ever contacted.
        outside = Path(tmp_path).parent / "definitely_outside_workspace.md"
        result = await session.call_tool(
            "analyze_project_context",
            {"paths": [str(outside)], "max_depth": 1},
        )

    # The MCP layer surfaces tool errors as isError=True (RuntimeError wrap).
    assert result.isError, "expected workspace-access refusal"
