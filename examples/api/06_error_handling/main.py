#!/usr/bin/env python3
"""06 — Error handling & retry (timeout / rate limit / network)."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

from common import get_client, get_config, is_retryable, retry_after_seconds, with_retry


class FakeResponse:
    def __init__(self, status_code: int, headers: dict | None = None) -> None:
        self.status_code = status_code
        self.headers = headers or {}
        self.request = None


def demo_classify() -> None:
    print("=== Retry classification ===")
    cases = [
        ("RateLimitError", RateLimitError("rate limited", response=FakeResponse(429, {"Retry-After": "2"}), body=None)),
        ("Timeout", APITimeoutError(request=None)),  # type: ignore[arg-type]
        ("Connection", APIConnectionError(message="dns", request=None)),  # type: ignore[arg-type]
        ("Auth 401", APIStatusError("unauthorized", response=FakeResponse(401), body=None)),
        ("Bad request 400", APIStatusError("bad", response=FakeResponse(400), body=None)),
        ("Upstream 503", APIStatusError("unavailable", response=FakeResponse(503), body=None)),
    ]
    for name, exc in cases:
        print(f"  {name:16} retryable={is_retryable(exc)}")


def demo_backoff() -> None:
    print("\n=== Backoff with Retry-After ===")
    exc = RateLimitError(
        "too many requests",
        response=FakeResponse(429, {"Retry-After": "1.5"}),
        body=None,
    )
    wait = retry_after_seconds(exc, attempt=1)
    print(f"  Retry-After honored → sleep {wait}s")
    time.sleep(min(wait, 0.2))  # keep demo snappy

    print("=== Backoff without Retry-After (exp + jitter) ===")
    for attempt in range(1, 4):
        w = retry_after_seconds(APITimeoutError(request=None), attempt=attempt)  # type: ignore[arg-type]
        print(f"  attempt={attempt} suggested_wait≈{w:.2f}s")


def demo_live_or_mock(client, model: str, mock: bool) -> None:
    print("\n=== Wrapped live call (with_retry) ===")

    def _call():
        if mock:
            # Simulate one transient failure then success
            if not getattr(_call, "_failed_once", False):
                _call._failed_once = True  # type: ignore[attr-defined]
                raise RateLimitError(
                    "mock 429",
                    response=FakeResponse(429, {"Retry-After": "0.1"}),
                    body=None,
                )
            return type(
                "R",
                (),
                {
                    "choices": [
                        type("C", (), {"message": type("M", (), {"content": "mock ok after retry"})()})()
                    ]
                },
            )()
        return client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "只回复：pong"}],
            max_tokens=16,
            temperature=0,
        )

    resp = with_retry(_call, max_attempts=4, max_total_wait=20.0, label="ping")
    content = resp.choices[0].message.content
    print(f"  success content={content!r}")


def main() -> None:
    cfg = get_config()
    client = get_client(cfg)

    print("Policy:")
    print("  - Retry: 408/429/5xx, timeout, connection errors")
    print("  - Do NOT retry: 400/401/402/403 (fix request or credentials)")
    print("  - Prefer Retry-After; else exponential backoff + jitter")
    print("  - Cap max_attempts and max_total_wait\n")

    demo_classify()
    demo_backoff()
    demo_live_or_mock(client, cfg.model, cfg.mock)


if __name__ == "__main__":
    main()
