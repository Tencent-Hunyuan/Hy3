"""Minimal, dependency-free client for Hy3's OpenAI-compatible API."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from .config import Settings


class Hy3Error(RuntimeError):
    """Safe provider error that never includes the API key."""


Transport = Callable[[urllib.request.Request, float], dict[str, Any]]


class Hy3Client:
    def __init__(self, settings: Settings, transport: Transport | None = None) -> None:
        if not settings.live_ready:
            raise ValueError("HY3_API_KEY is required for live mode")
        self.settings = settings
        self.transport = transport or _default_transport

    def complete_json(
        self, *, system: str, user: str, max_tokens: int = 2_800
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        payload = {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            f"{self.settings.base_url}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "hy3-scenarioforge/0.1",
            },
            method="POST",
        )
        response = self._request_with_retry(request)
        try:
            choice = response["choices"][0]
            content = choice["message"]["content"]
            parsed = json.loads(_strip_json_fence(content))
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            raise Hy3Error("Hy3 returned an invalid structured response") from error
        if not isinstance(parsed, dict):
            raise Hy3Error("Hy3 returned JSON that was not an object")
        metadata = {
            "model": response.get("model", self.settings.model),
            "request_id": response.get("id"),
            "usage": response.get("usage", {}),
        }
        return parsed, metadata

    def _request_with_retry(self, request: urllib.request.Request) -> dict[str, Any]:
        for attempt in range(2):
            try:
                return self.transport(request, self.settings.timeout_seconds)
            except urllib.error.HTTPError as error:
                if error.code in {401, 403}:
                    raise Hy3Error("Hy3 authentication failed; check HY3_API_KEY") from None
                if error.code not in {408, 429, 500, 502, 503, 504} or attempt == 1:
                    raise Hy3Error(f"Hy3 request failed with HTTP {error.code}") from None
            except (urllib.error.URLError, TimeoutError):
                if attempt == 1:
                    raise Hy3Error("Hy3 endpoint could not be reached after retry") from None
            time.sleep(0.25)
        raise AssertionError("retry loop exhausted")


def _default_transport(request: urllib.request.Request, timeout: float) -> dict[str, Any]:
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise Hy3Error("Hy3 API returned a non-object response")
    return parsed


def _strip_json_fence(content: Any) -> str:
    if not isinstance(content, str):
        raise TypeError("message content must be text")
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1])
    return stripped
