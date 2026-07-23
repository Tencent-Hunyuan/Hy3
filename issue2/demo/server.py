#!/usr/bin/env python3
"""Dependency-free HTTP server for Hy3 Evidence Board."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from evidence_board import (
    DemoProvider,
    KnowledgeBase,
    ProviderError,
    ResearchAgent,
    ValidationError,
    provider_from_environment,
)


ROOT = Path(__file__).resolve().parent
STATIC_ROOT = ROOT / "static"
KNOWLEDGE_ROOT = ROOT / "knowledge"
MAX_REQUEST_BYTES = 32 * 1024


def build_agent() -> ResearchAgent:
    return ResearchAgent(provider_from_environment(), KnowledgeBase.from_directory(KNOWLEDGE_ROOT))


class EvidenceBoardHandler(BaseHTTPRequestHandler):
    server_version = "Hy3EvidenceBoard/1.0"
    agent: ResearchAgent

    def log_message(self, format: str, *args: object) -> None:
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), format % args))

    def send_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/api/health":
            self.send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "mode": self.agent.provider.mode,
                    "model": getattr(self.agent.provider, "model", "offline-demo"),
                },
            )
            return
        if path == "/":
            path = "/index.html"
        relative = Path(path.lstrip("/"))
        if any(part in {"..", "."} for part in relative.parts):
            self.send_error(HTTPStatus.NOT_FOUND.value)
            return
        target = (STATIC_ROOT / relative).resolve()
        if STATIC_ROOT.resolve() not in target.parents or not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND.value)
            return
        body = target.read_bytes()
        content_type, _ = mimetypes.guess_type(target.name)
        self.send_response(HTTPStatus.OK.value)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/api/research":
            self.send_error(HTTPStatus.NOT_FOUND.value)
            return
        content_type = self.headers.get_content_type()
        if content_type != "application/json":
            self.send_json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"ok": False, "error": "Content-Type 必须是 application/json。"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "Content-Length 无效。"})
            return
        if length <= 0 or length > MAX_REQUEST_BYTES:
            self.send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"ok": False, "error": "请求体为空或过大。"})
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "请求体不是有效 JSON。"})
            return
        if not isinstance(payload, dict):
            self.send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "JSON 顶层必须是对象。"})
            return
        try:
            result = self.agent.run(payload.get("question"))
        except ValidationError as exc:
            self.send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
            return
        except ProviderError as exc:
            self.send_json(HTTPStatus.BAD_GATEWAY, {"ok": False, "error": str(exc)})
            return
        self.send_json(HTTPStatus.OK, {"ok": True, **result})


def make_server(host: str, port: int, agent: ResearchAgent | None = None) -> ThreadingHTTPServer:
    handler = type("ConfiguredEvidenceBoardHandler", (EvidenceBoardHandler,), {"agent": agent or build_agent()})
    return ThreadingHTTPServer((host, port), handler)


def run_check() -> int:
    agent = ResearchAgent(DemoProvider(), KnowledgeBase.from_directory(KNOWLEDGE_ROOT))
    result = agent.run("请解释 Hy3 的模型规模、上下文长度以及 Agent 工具调用部署要求。")
    if result["mode"] != "demo" or not result["trace"] or not result["evidence"]:
        print("self-check failed", file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, "mode": result["mode"], "evidence": len(result["evidence"]), "trace": result["trace"]}, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Hy3 Evidence Board")
    parser.add_argument("--host", default=os.getenv("HY3_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("HY3_PORT", "8765")))
    parser.add_argument("--check", action="store_true", help="run a deterministic offline self-check")
    args = parser.parse_args()
    if args.check:
        return run_check()
    try:
        server = make_server(args.host, args.port)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"Hy3 Evidence Board ({server.RequestHandlerClass.agent.provider.mode}) -> http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
