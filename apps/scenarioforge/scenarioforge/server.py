"""Small same-origin web server for ScenarioForge."""

from __future__ import annotations

import argparse
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .config import Settings
from .examples import EXAMPLES, DemoClient, public_examples
from .hy3 import Hy3Client, Hy3Error
from .models import ContractError, RehearsalRequest
from .service import RehearsalService

STATIC_ROOT = Path(__file__).parent / "static"
STATIC_ROUTES = {
    "/": "index.html",
    "/index.html": "index.html",
    "/app.js": "app.js",
    "/styles.css": "styles.css",
    "/favicon.svg": "favicon.svg",
}
MAX_BODY_BYTES = 32_768


class ScenarioForgeHandler(BaseHTTPRequestHandler):
    settings: Settings

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/health":
            mode = "demo" if self.settings.demo_mode else "live"
            self._json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "mode": mode,
                    "live_ready": self.settings.live_ready,
                    "model": self.settings.model,
                },
            )
            return
        if self.path == "/api/examples":
            self._json(HTTPStatus.OK, {"examples": public_examples()})
            return
        static_name = STATIC_ROUTES.get(self.path)
        if static_name:
            self._static(static_name)
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "route not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/rehearse":
            self._json(HTTPStatus.NOT_FOUND, {"error": "route not found"})
            return
        try:
            payload = self._read_json()
            request = RehearsalRequest.from_json(payload)
            if self.settings.demo_mode:
                self._verify_demo_request(request)
                client = DemoClient(request.example_id or "")
            else:
                if not self.settings.live_ready:
                    self._json(
                        HTTPStatus.SERVICE_UNAVAILABLE,
                        {
                            "error": "HY3_API_KEY is not configured",
                            "hint": "Set Hy3 credentials or start with SCENARIOFORGE_DEMO_MODE=1",
                        },
                    )
                    return
                client = Hy3Client(self.settings)
            result = RehearsalService(client).run(request)
            if self.settings.demo_mode:
                result["mode"] = "demo"
                result["provider"] = {
                    "name": "Bundled offline fixture",
                    "model": "offline-fixture",
                    "calls": 0,
                    "request_ids": [],
                    "usage": {},
                }
            self._json(HTTPStatus.OK, result)
        except ContractError as error:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        except Hy3Error as error:
            self._json(HTTPStatus.BAD_GATEWAY, {"error": str(error)})
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._json(HTTPStatus.BAD_REQUEST, {"error": "request body must be valid UTF-8 JSON"})

    def _verify_demo_request(self, request: RehearsalRequest) -> None:
        if not request.example_id or request.example_id not in EXAMPLES:
            raise ContractError("demo mode only accepts one of the bundled examples")
        expected = EXAMPLES[request.example_id]
        comparable = request.as_prompt_payload()
        expected_input = {
            key: expected[key] for key in ("title", "goal", "plan", "constraints")
        }
        if comparable != expected_input:
            raise ContractError("edited inputs require live Hy3 mode; reload the bundled example")

    def _read_json(self) -> Any:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0]
        if content_type != "application/json":
            raise ContractError("Content-Type must be application/json")
        raw_length = self.headers.get("Content-Length")
        if not raw_length:
            raise ContractError("Content-Length is required")
        try:
            length = int(raw_length)
        except ValueError as error:
            raise ContractError("Content-Length must be an integer") from error
        if length <= 0 or length > MAX_BODY_BYTES:
            raise ContractError(f"request body must be between 1 and {MAX_BODY_BYTES} bytes")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _static(self, filename: str) -> None:
        path = STATIC_ROOT / filename
        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        content_security_policy = (
            "default-src 'self'; style-src 'self'; script-src 'self'; "
            "connect-src 'self'; img-src 'self' data:"
        )
        self.send_header("Content-Security-Policy", content_security_policy)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: HTTPStatus, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[scenarioforge] {self.address_string()} {format % args}")


def create_server(host: str, port: int, settings: Settings) -> ThreadingHTTPServer:
    handler = type(
        "ConfiguredScenarioForgeHandler", (ScenarioForgeHandler,), {"settings": settings}
    )
    return ThreadingHTTPServer((host, port), handler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Hy3 ScenarioForge web application")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    settings = Settings.from_env()
    server = create_server(args.host, args.port, settings)
    mode = "demo fixture" if settings.demo_mode else "live Hy3"
    print(f"ScenarioForge ({mode}) → http://{args.host}:{server.server_address[1]}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
