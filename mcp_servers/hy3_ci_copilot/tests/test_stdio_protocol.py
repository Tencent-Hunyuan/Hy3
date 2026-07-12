from __future__ import annotations

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

EXPECTED_TOOLS = {
    "diagnose_ci_failure",
    "compare_ci_runs",
    "review_ci_workflow",
    "build_ci_fix_plan",
}


class FakeHy3Handler(BaseHTTPRequestHandler):
    requests: ClassVar[list[dict]] = []

    def do_POST(self) -> None:
        length = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(length))
        self.requests.append({"path": self.path, "body": body})
        payload = json.dumps(
            {"choices": [{"message": {"content": f"Hy3 call {len(self.requests)}"}}]}
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, _format: str, *_args) -> None:
        return


@pytest.mark.asyncio
async def test_stdio_server_lists_and_calls_all_tools(repository: Path) -> None:
    FakeHy3Handler.requests = []
    http_server = ThreadingHTTPServer(("127.0.0.1", 0), FakeHy3Handler)
    thread = threading.Thread(target=http_server.serve_forever, daemon=True)
    thread.start()

    src = Path(__file__).parents[1] / "src"
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(filter(None, [str(src), os.getenv("PYTHONPATH", "")])),
        "HY3_API_KEY": "stdio-test-key",
        "HY3_BASE_URL": f"http://127.0.0.1:{http_server.server_port}/v1",
        "HY3_MODEL": "hy3-test",
        "HY3_ALLOWED_ROOTS": str(repository),
        "HY3_MAX_RETRIES": "0",
        "NO_PROXY": "127.0.0.1,localhost",
    }
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "hy3_ci_copilot"],
        env=env,
    )

    try:
        async with (
            stdio_client(parameters) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            listed = await session.list_tools()
            tools = {tool.name: tool for tool in listed.tools}
            assert set(tools) == EXPECTED_TOOLS
            assert all(tool.description for tool in tools.values())
            assert all(tool.inputSchema.get("properties") for tool in tools.values())

            calls = [
                (
                    "diagnose_ci_failure",
                    {"log_path": "failed.log", "repository_path": str(repository)},
                ),
                (
                    "compare_ci_runs",
                    {
                        "failed_log_path": "failed.log",
                        "successful_log_path": "successful.log",
                        "repository_path": str(repository),
                    },
                ),
                (
                    "review_ci_workflow",
                    {
                        "workflow_path": ".github/workflows/ci.yml",
                        "repository_path": str(repository),
                    },
                ),
                (
                    "build_ci_fix_plan",
                    {
                        "diagnosis": "The test dependency cannot be imported.",
                        "repository_path": str(repository),
                    },
                ),
            ]
            for index, (name, arguments) in enumerate(calls, start=1):
                result = await session.call_tool(name, arguments=arguments)
                assert not result.isError
                assert result.content[0].text == f"Hy3 call {index}"

            denied = await session.call_tool(
                "diagnose_ci_failure",
                {
                    "log_path": "../outside.log",
                    "repository_path": str(repository),
                },
            )
            assert denied.isError
    finally:
        http_server.shutdown()
        thread.join(timeout=5)
        http_server.server_close()

    assert len(FakeHy3Handler.requests) == 4
    assert all(request["path"] == "/v1/chat/completions" for request in FakeHy3Handler.requests)
    assert all(request["body"]["model"] == "hy3-test" for request in FakeHy3Handler.requests)
