"""
Shared helpers for Hy3 API examples.

Supports both:
  - Cloud TokenHub (OpenAI-compatible): https://tokenhub.tencentmaas.com/v1
  - Local vLLM / SGLang:                http://127.0.0.1:8000/v1

Environment variables (all optional with defaults):
  HY3_BASE_URL   default http://127.0.0.1:8000/v1
  HY3_API_KEY    default EMPTY
  HY3_MODEL      default hy3
  HY3_TIMEOUT    default 120 (seconds)
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "http://127.0.0.1:8000/v1"
DEFAULT_API_KEY = "EMPTY"
DEFAULT_MODEL = "hy3"
DEFAULT_TIMEOUT = 120.0

# Cloud TokenHub (document only; set via env when using hosted API)
TOKENHUB_BASE_URL = "https://tokenhub.tencentmaas.com/v1"

RETRYABLE_ERRORS = (APITimeoutError, RateLimitError, APIConnectionError)


def get_config() -> Dict[str, Any]:
    """Read connection config from environment variables."""
    timeout_raw = os.environ.get("HY3_TIMEOUT", str(DEFAULT_TIMEOUT))
    try:
        timeout = float(timeout_raw)
    except ValueError:
        timeout = DEFAULT_TIMEOUT
    return {
        "base_url": os.environ.get("HY3_BASE_URL", DEFAULT_BASE_URL),
        "api_key": os.environ.get("HY3_API_KEY", DEFAULT_API_KEY),
        "model": os.environ.get("HY3_MODEL", DEFAULT_MODEL),
        "timeout": timeout,
    }


def make_client(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: Optional[float] = None,
) -> OpenAI:
    """Create an OpenAI-compatible client for Hy3."""
    cfg = get_config()
    return OpenAI(
        base_url=base_url if base_url is not None else cfg["base_url"],
        api_key=api_key if api_key is not None else cfg["api_key"],
        timeout=timeout if timeout is not None else cfg["timeout"],
    )


# ---------------------------------------------------------------------------
# Reasoning / thinking switch (local + cloud dual compatibility)
# ---------------------------------------------------------------------------

# Map high-level modes to both cloud TokenHub and local vLLM/SGLang params.
REASONING_MODES = {
    "off": {"thinking_type": "disabled", "reasoning_effort": "no_think"},
    "no_think": {"thinking_type": "disabled", "reasoning_effort": "no_think"},
    "low": {"thinking_type": "enabled", "reasoning_effort": "low"},
    "high": {"thinking_type": "enabled", "reasoning_effort": "high"},
    "on": {"thinking_type": "enabled", "reasoning_effort": "high"},
}


def build_extra_body(reasoning: str = "no_think", **extra: Any) -> Dict[str, Any]:
    """Build extra_body that works on both TokenHub and local deployments.

    - Cloud TokenHub: reads top-level ``thinking: {type: enabled|disabled}``
    - Local vLLM/SGLang: reads ``chat_template_kwargs.reasoning_effort``
      (no_think / low / high)

    Both forms are sent together so the same example runs without code changes.
    Unknown keys in *extra* are merged on top.
    """
    mode = REASONING_MODES.get(reasoning)
    if mode is None:
        raise ValueError(
            f"Unknown reasoning mode {reasoning!r}. "
            f"Expected one of: {sorted(REASONING_MODES)}"
        )
    body: Dict[str, Any] = {
        "thinking": {"type": mode["thinking_type"]},
        "chat_template_kwargs": {"reasoning_effort": mode["reasoning_effort"]},
    }
    body.update(extra)
    return body


def chat_completion(
    client: OpenAI,
    messages: Sequence[Dict[str, Any]],
    *,
    model: Optional[str] = None,
    reasoning: str = "no_think",
    temperature: float = 0.9,
    top_p: float = 1.0,
    max_tokens: Optional[int] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    stream: bool = False,
    stop: Optional[Any] = None,
    **kwargs: Any,
):
    """Thin wrapper around chat.completions.create with Hy3 defaults."""
    cfg = get_config()
    create_kwargs: Dict[str, Any] = {
        "model": model or cfg["model"],
        "messages": list(messages),
        "temperature": temperature,
        "top_p": top_p,
        "extra_body": build_extra_body(reasoning),
        "stream": stream,
    }
    if max_tokens is not None:
        create_kwargs["max_tokens"] = max_tokens
    if tools is not None:
        create_kwargs["tools"] = tools
    if stop is not None:
        create_kwargs["stop"] = stop
    create_kwargs.update(kwargs)
    return client.chat.completions.create(**create_kwargs)


# ---------------------------------------------------------------------------
# Streaming helpers
# ---------------------------------------------------------------------------


def iter_stream_text(stream: Iterable[Any]) -> Iterable[str]:
    """Yield non-empty text deltas from a streaming chat completion."""
    for chunk in stream:
        if not getattr(chunk, "choices", None):
            continue
        delta = chunk.choices[0].delta
        content = getattr(delta, "content", None)
        if content:
            yield content


def collect_stream(
    stream: Iterable[Any],
) -> Tuple[str, Optional[float], float]:
    """Collect a stream into full text, TTFT (seconds), and total latency.

    Returns:
        (full_text, ttft_seconds_or_None, total_seconds)
    """
    t0 = time.perf_counter()
    parts: List[str] = []
    ttft: Optional[float] = None
    for text in iter_stream_text(stream):
        if ttft is None:
            ttft = time.perf_counter() - t0
        parts.append(text)
    total = time.perf_counter() - t0
    return "".join(parts), ttft, total


def extract_reasoning_and_content(message: Any) -> Tuple[Optional[str], Optional[str]]:
    """Return (reasoning_content, content) from an assistant message."""
    reasoning = getattr(message, "reasoning_content", None)
    content = getattr(message, "content", None)
    return reasoning, content


# ---------------------------------------------------------------------------
# Tool-calling loop
# ---------------------------------------------------------------------------


def run_tool_loop(
    client: OpenAI,
    messages: List[Any],
    tools: List[Dict[str, Any]],
    available_functions: Dict[str, Callable[..., Any]],
    *,
    model: Optional[str] = None,
    max_iterations: int = 5,
    reasoning: str = "no_think",
    temperature: float = 0.9,
    top_p: float = 1.0,
    on_tool_call: Optional[Callable[[Any, Any], None]] = None,
) -> Any:
    """Execute a bounded multi-turn tool-calling loop.

    Appends assistant tool_calls messages and tool results in-place to *messages*.
    Returns the final assistant message (without tool_calls), or the last message
    if max_iterations is hit.
    """
    last_message = None
    for _ in range(max_iterations):
        response = chat_completion(
            client,
            messages,
            model=model,
            tools=tools,
            reasoning=reasoning,
            temperature=temperature,
            top_p=top_p,
        )
        message = response.choices[0].message
        last_message = message

        if not message.tool_calls:
            messages.append(message)
            return message

        # Keep the assistant message with tool_calls in history as-is
        messages.append(message)

        for tool_call in message.tool_calls:
            func_name = tool_call.function.name
            raw_args = tool_call.function.arguments
            try:
                func_args = json.loads(raw_args) if raw_args else {}
            except json.JSONDecodeError:
                func_args = {}

            func = available_functions.get(func_name)
            if func is None:
                result = f"Error: unknown tool {func_name}"
            else:
                try:
                    result = func(**func_args)
                except TypeError as exc:
                    result = f"Error calling {func_name}: {exc}"

            if on_tool_call is not None:
                on_tool_call(tool_call, result)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(result),
                }
            )

    return last_message


# ---------------------------------------------------------------------------
# Retry with exponential backoff (+ optional Retry-After)
# ---------------------------------------------------------------------------


def parse_retry_after(error: BaseException) -> Optional[float]:
    """Extract Retry-After seconds from an HTTP error if present."""
    response = getattr(error, "response", None)
    if response is None:
        return None
    headers = getattr(response, "headers", None) or {}
    # httpx / requests style case-insensitive mapping
    value = None
    if hasattr(headers, "get"):
        value = headers.get("Retry-After") or headers.get("retry-after")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def call_with_retry(
    fn: Callable[[], Any],
    *,
    max_attempts: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    max_total_wait: float = 60.0,
    retryable: Tuple[type, ...] = RETRYABLE_ERRORS,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> Any:
    """Call *fn* with exponential backoff on transient errors.

    Honors ``Retry-After`` when present on RateLimitError / APIStatusError.
    Caps both per-sleep delay and total wait time so demos never hang forever.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    attempt = 0
    waited = 0.0
    last_error: Optional[BaseException] = None

    while attempt < max_attempts:
        attempt += 1
        try:
            return fn()
        except retryable as exc:
            last_error = exc
            if attempt >= max_attempts:
                break
            # Exponential: base * 2^(attempt-1), capped by max_delay
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            retry_after = parse_retry_after(exc)
            if retry_after is not None:
                delay = max(delay, retry_after)
            # Respect total wait budget
            remaining = max_total_wait - waited
            if remaining <= 0:
                break
            delay = min(delay, remaining)
            sleep_fn(delay)
            waited += delay
        except APIStatusError as exc:
            # Retry 5xx; do not retry other 4xx (except 429 which is RateLimitError)
            status = getattr(exc, "status_code", None)
            if status is not None and 500 <= int(status) < 600:
                last_error = exc
                if attempt >= max_attempts:
                    break
                delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
                remaining = max_total_wait - waited
                if remaining <= 0:
                    break
                delay = min(delay, remaining)
                sleep_fn(delay)
                waited += delay
                continue
            raise

    assert last_error is not None
    raise last_error


def redacted_preview(text: Optional[str], max_len: int = 80) -> str:
    """Short preview for logs; never echoes secrets (API keys look like sk-...)."""
    if not text:
        return ""
    cleaned = text
    # Cheap redaction for common key patterns accidentally printed
    if "sk-" in cleaned:
        cleaned = "[redacted]"
    if len(cleaned) > max_len:
        return cleaned[: max_len - 3] + "..."
    return cleaned
