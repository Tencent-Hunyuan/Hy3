"""Shared helpers for Hy3 TokenHub API examples."""

from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypeVar

from dotenv import load_dotenv
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI, RateLimitError

# Load .env next to this file (examples/api/.env)
load_dotenv(Path(__file__).resolve().parent / ".env")

T = TypeVar("T")

DEFAULT_BASE_URL = "https://tokenhub.tencentmaas.com/v1"
DEFAULT_MODEL = "hy3"


@dataclass(frozen=True)
class Config:
    api_key: str
    base_url: str
    model: str
    mock: bool


def get_config() -> Config:
    mock = os.getenv("HY3_MOCK", "").strip().lower() in {"1", "true", "yes"}
    api_key = os.getenv("HY3_API_KEY", "").strip()
    if not api_key and not mock:
        raise SystemExit(
            "Missing HY3_API_KEY. Export it, or copy .env.example to .env.\n"
            "For offline syntax check: HY3_MOCK=1 python <example>/main.py"
        )
    return Config(
        api_key=api_key or "mock-key",
        base_url=os.getenv("HY3_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
        model=os.getenv("HY3_MODEL", DEFAULT_MODEL),
        mock=mock,
    )


def get_client(cfg: Config | None = None) -> OpenAI:
    cfg = cfg or get_config()
    return OpenAI(api_key=cfg.api_key, base_url=cfg.base_url, timeout=60.0)


def redact(text: str | None, keep: int = 120) -> str:
    """Shorten long sample output for docs / console."""
    if not text:
        return ""
    text = text.strip()
    if len(text) <= keep:
        return text
    return text[:keep] + "…"


def message_to_dict(msg: Any) -> dict[str, Any]:
    """Serialize an assistant message, preserving reasoning_content for tool loops."""
    data: dict[str, Any] = {
        "role": msg.role,
        "content": msg.content,
    }
    reasoning = getattr(msg, "reasoning_content", None)
    if reasoning:
        data["reasoning_content"] = reasoning

    if getattr(msg, "tool_calls", None):
        data["tool_calls"] = [
            {
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in msg.tool_calls
        ]
    return data


def dump_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, (APIConnectionError, APITimeoutError, RateLimitError)):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code in {408, 429, 500, 502, 503, 504}
    return False


def retry_after_seconds(exc: BaseException, attempt: int, base: float = 1.0) -> float:
    """Prefer Retry-After; otherwise exponential backoff with jitter."""
    if isinstance(exc, APIStatusError):
        header = None
        try:
            header = exc.response.headers.get("Retry-After")
        except Exception:
            header = None
        if header:
            try:
                return max(0.0, float(header))
            except ValueError:
                pass
    # attempt starts at 1
    delay = base * (2 ** (attempt - 1))
    return delay + random.uniform(0, 0.5)


def with_retry(
    fn: Callable[[], T],
    *,
    max_attempts: int = 4,
    max_total_wait: float = 30.0,
    label: str = "request",
) -> T:
    """Run fn with limited retries for transient failures."""
    started = time.monotonic()
    last_exc: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - surface retry decision clearly
            last_exc = exc
            if not is_retryable(exc) or attempt >= max_attempts:
                raise
            wait = retry_after_seconds(exc, attempt)
            elapsed = time.monotonic() - started
            if elapsed + wait > max_total_wait:
                raise RuntimeError(
                    f"{label} aborted: would exceed max_total_wait={max_total_wait}s"
                ) from exc
            print(
                f"[retry] {label} attempt {attempt}/{max_attempts} failed: "
                f"{type(exc).__name__}: {exc}. sleep {wait:.2f}s"
            )
            time.sleep(wait)
    assert last_exc is not None
    raise last_exc


class MockMessage:
    def __init__(
        self,
        content: str | None = None,
        *,
        role: str = "assistant",
        reasoning_content: str | None = None,
        tool_calls: list[Any] | None = None,
    ) -> None:
        self.role = role
        self.content = content
        self.reasoning_content = reasoning_content
        self.tool_calls = tool_calls


class MockToolCall:
    def __init__(self, name: str, arguments: str, call_id: str = "call_mock_1") -> None:
        self.id = call_id
        self.type = "function"
        self.function = type("Fn", (), {"name": name, "arguments": arguments})()


class MockChoice:
    def __init__(self, message: MockMessage, finish_reason: str = "stop") -> None:
        self.message = message
        self.finish_reason = finish_reason
        self.delta = message  # reuse for stream-like demos when needed


class MockUsage:
    def __init__(self, prompt: int = 20, completion: int = 40) -> None:
        self.prompt_tokens = prompt
        self.completion_tokens = completion
        self.total_tokens = prompt + completion


class MockResponse:
    def __init__(
        self,
        message: MockMessage,
        *,
        finish_reason: str = "stop",
        model: str = DEFAULT_MODEL,
    ) -> None:
        self.id = "chatcmpl-mock"
        self.model = model
        self.choices = [MockChoice(message, finish_reason)]
        self.usage = MockUsage()
