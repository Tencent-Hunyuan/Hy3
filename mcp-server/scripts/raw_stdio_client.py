# Copyright 2026 Tencent Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Raw JSON-RPC stdio MCP client — deliberately ZERO ``mcp`` imports.

This is the project's independent second MCP client: it speaks the MCP
stdio wire format directly (newline-delimited JSON-RPC 2.0 over a child
process's stdin/stdout), proving the server is protocol-correct without
relying on the official SDK on the client side.

Usage as a library (used by tests and by scripts/record_demo.py)::

    with RawStdioClient([sys.executable, "-m", "hy3_mcp"], env=..., cwd=...) as c:
        c.initialize()
        print(c.list_tools())
        print(c.call_tool("hy3_status"))

Usage as a script (runs a small offline demo flow)::

    python scripts/raw_stdio_client.py
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

PROTOCOL_VERSION = "2025-06-18"  # a widely supported MCP protocol revision
CLIENT_INFO = {"name": "raw-jsonrpc-stdio-client", "version": "0.1.0"}


class RawStdioClient:
    """Minimal blocking MCP client over newline-delimited JSON-RPC stdio."""

    def __init__(
        self,
        command: list[str],
        env: dict[str, str] | None = None,
        cwd: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.timeout = timeout
        self._next_id = 0
        self.proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,  # server banners must not block the pipe
            env=env,
            cwd=cwd,
            text=True,
            bufsize=1,
        )
        self._lines: "queue.Queue[str | None]" = queue.Queue()
        self._reader = threading.Thread(target=self._pump, daemon=True)
        self._reader.start()

    # -- plumbing ---------------------------------------------------------

    def _pump(self) -> None:
        assert self.proc.stdout is not None
        for line in self.proc.stdout:
            self._lines.put(line)
        self._lines.put(None)  # EOF sentinel

    def _send(self, message: dict[str, Any]) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        msg: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        self._send(msg)

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send a request and block until its response arrives (skipping
        any server-initiated notifications such as log messages)."""
        self._next_id += 1
        rid = self._next_id
        msg: dict[str, Any] = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:
            msg["params"] = params
        self._send(msg)
        while True:
            line = self._lines.get(timeout=self.timeout)
            if line is None:
                raise RuntimeError("server closed stdout before responding")
            line = line.strip()
            if not line:
                continue
            reply = json.loads(line)  # non-JSON on stdout = protocol violation
            if reply.get("id") != rid:
                continue  # notification or unrelated message
            if "error" in reply:
                raise RuntimeError(f"JSON-RPC error: {reply['error']}")
            return reply["result"]

    # -- MCP flow ---------------------------------------------------------

    def initialize(self) -> dict[str, Any]:
        result = self.request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": CLIENT_INFO,
            },
        )
        self.notify("notifications/initialized")
        return result

    def list_tools(self) -> dict[str, Any]:
        return self.request("tools/list")

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.request("tools/call", {"name": name, "arguments": arguments or {}})

    def close(self) -> None:
        try:
            if self.proc.stdin is not None:
                self.proc.stdin.close()
            self.proc.terminate()
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()

    def __enter__(self) -> "RawStdioClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def _demo() -> int:
    """Drive an offline demo flow against the real server as a subprocess."""
    mcp_server_dir = Path(__file__).resolve().parents[1]
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "PYTHONPATH": str(mcp_server_dir / "src"),
        "HY3_MCP_OFFLINE": "1",
        "HY3_MCP_ROOT": str(mcp_server_dir),
    }
    with RawStdioClient(
        [sys.executable, "-m", "hy3_mcp"], env=env, cwd=str(mcp_server_dir)
    ) as client:
        init = client.initialize()
        print(f"server   : {init['serverInfo']['name']} (protocol {init['protocolVersion']})")
        tools = client.list_tools()["tools"]
        print(f"tools    : {', '.join(t['name'] for t in tools)}")
        status = client.call_tool("hy3_status")["structuredContent"]
        print(f"status   : mode={status['mode']} model={status['model']}")
        review = client.call_tool("review_code", {"path": "examples/diffs/demo.diff"})
        flags = review["structuredContent"]["heuristic_flags"]
        print(f"review   : {len(flags)} heuristic flag(s)")
        print(review["structuredContent"]["markdown"].splitlines()[0])
    return 0


if __name__ == "__main__":
    sys.exit(_demo())
