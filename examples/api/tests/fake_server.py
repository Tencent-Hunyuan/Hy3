from __future__ import annotations

import json
import threading
from collections import deque
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Iterable, Mapping


@dataclass
class QueuedResponse:
    status: int
    headers: dict[str, str]
    body: bytes


class _TestHTTPServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        requests: list[dict[str, Any]],
        responses: deque[QueuedResponse],
    ) -> None:
        super().__init__(server_address, _Handler)
        self.requests = requests
        self.responses = responses


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            self._send_json(400, {"error": "invalid JSON"})
            return

        server = self.server
        if not isinstance(server, _TestHTTPServer):
            self._send_json(500, {"error": "invalid test server"})
            return

        server.requests.append({"path": self.path, "json": payload})

        if self.path != "/v1/chat/completions":
            self._send_json(404, {"error": "not found"})
            return

        if not server.responses:
            self._send_json(500, {"error": "no queued response"})
            return

        response = server.responses.popleft()
        self.send_response(response.status)
        for name, value in response.headers.items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(response.body)))
        self.end_headers()
        self.wfile.write(response.body)
        self.wfile.flush()

    def _send_json(self, status: int, payload: Mapping[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()

    def log_message(self, format: str, *args: object) -> None:
        """静默测试服务器的默认请求日志。"""


class FakeOpenAIServer:
    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.base_url = ""
        self.responses: deque[QueuedResponse] = deque()
        self.server: _TestHTTPServer | None = None
        self.thread: threading.Thread | None = None

    def enqueue_json(
        self,
        payload: Mapping[str, Any],
        *,
        status: int = 200,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        response_headers = {"Content-Type": "application/json"}
        if headers is not None:
            response_headers.update(headers)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.responses.append(QueuedResponse(status, response_headers, body))

    def enqueue_sse(
        self,
        events: Iterable[Mapping[str, Any]],
        *,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        body = "".join(
            f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            for event in events
        )
        body += "data: [DONE]\n\n"
        self.responses.append(
            QueuedResponse(
                status=200,
                headers={
                    "Content-Type": "text/event-stream",
                    "Cache-Control": "no-cache",
                    **dict(headers or {}),
                },
                body=body.encode("utf-8"),
            )
        )

    def __enter__(self) -> FakeOpenAIServer:
        self.server = _TestHTTPServer(
            ("127.0.0.1", 0),
            self.requests,
            self.responses,
        )
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}/v1"
        self.thread = threading.Thread(
            target=self.server.serve_forever,
            daemon=True,
        )
        self.thread.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object,
    ) -> None:
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=5)
