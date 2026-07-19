"""
Shared helpers for Hy3 API examples.

Supports both:
  - Cloud TokenHub (OpenAI-compatible): https://tokenhub.tencentmaas.com/v1
  - Local vLLM / SGLang:                http://127.0.0.1:8000/v1

Environment variables (all optional with defaults for local demos):
  HY3_BASE_URL   default http://127.0.0.1:8000/v1
  HY3_API_KEY    default EMPTY
  HY3_MODEL      default hy3
  HY3_TIMEOUT    default 120 (seconds)
"""

from __future__ import annotations

import json
import os
import random
import re
import time
from email.utils import parsedate_to_datetime
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlsplit

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
RETRYABLE_STATUS_CODES = frozenset({429, 502, 503, 504})

_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_SK_PATTERN = re.compile(r"\bsk-[A-Za-z0-9]{8,}\b")
_SENSITIVE_KEY_FRAGMENTS = (
    "api_key",
    "apikey",
    "authorization",
    "token",
    "secret",
    "password",
    "cookie",
)


def get_config() -> Dict[str, Any]:
    """Read connection config from environment variables."""
    timeout_raw = os.environ.get("HY3_TIMEOUT", str(DEFAULT_TIMEOUT))
    try:
        timeout = float(timeout_raw)
    except ValueError:
        timeout = DEFAULT_TIMEOUT
    if timeout <= 0:
        timeout = DEFAULT_TIMEOUT
    return {
        "base_url": os.environ.get("HY3_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
        "api_key": os.environ.get("HY3_API_KEY", DEFAULT_API_KEY),
        "model": os.environ.get("HY3_MODEL", DEFAULT_MODEL),
        "timeout": timeout,
    }


def validate_config(
    cfg: Optional[Dict[str, Any]] = None,
    *,
    require_api_key: bool = False,
) -> Dict[str, Any]:
    """Validate config for safer demos.

    - base_url must be absolute http(s)
    - remote hosts should use https (localhost/127.0.0.1 may use http)
    - when require_api_key=True (TokenHub path), reject EMPTY/placeholder keys
    """
    cfg = dict(cfg or get_config())
    base = (cfg.get("base_url") or "").strip()
    parsed = urlsplit(base)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"HY3_BASE_URL must be an absolute http(s) URL, got: {base!r}")
    host = (parsed.hostname or "").lower()
    local_hosts = {"127.0.0.1", "localhost", "::1"}
    if parsed.scheme == "http" and host not in local_hosts:
        raise ValueError(
            "Remote HY3_BASE_URL must use HTTPS "
            f"(got http://{host}). Local demos may use http://127.0.0.1."
        )
    if parsed.username or parsed.password:
        raise ValueError("HY3_BASE_URL must not embed credentials.")

    key = (cfg.get("api_key") or "").strip()
    if require_api_key and (
        not key or key.upper() in {"EMPTY", "YOUR_API_KEY", "REPLACE_ME", "SK-XXXX"}
    ):
        raise ValueError(
            "HY3_API_KEY is required for hosted TokenHub. "
            "Export it in your shell; never commit keys."
        )
    cfg["api_key"] = key or DEFAULT_API_KEY
    cfg["base_url"] = base.rstrip("/")
    return cfg


def make_client(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: Optional[float] = None,
    *,
    require_api_key: bool = False,
) -> OpenAI:
    """Create an OpenAI-compatible client for Hy3.

    SDK auto-retries are disabled (max_retries=0) so example retry logic is explicit.
    """
    cfg = get_config()
    if base_url is not None:
        cfg["base_url"] = base_url
    if api_key is not None:
        cfg["api_key"] = api_key
    if timeout is not None:
        cfg["timeout"] = timeout
    cfg = validate_config(cfg, require_api_key=require_api_key)
    return OpenAI(
        base_url=cfg["base_url"],
        api_key=cfg["api_key"],
        timeout=cfg["timeout"],
        max_retries=0,
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
            f"Unknown reasoning mode {reasoning!r}. Expected one of: {sorted(REASONING_MODES)}"
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
    if max_iterations < 1:
        raise ValueError("max_iterations must be >= 1")

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

            if not isinstance(func_args, dict):
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
# Retry with exponential backoff (+ optional Retry-After + jitter)
# ---------------------------------------------------------------------------


def parse_retry_after(error: BaseException) -> Optional[float]:
    """Extract Retry-After seconds from an HTTP error if present.

    Supports integer/float seconds and HTTP-date values (RFC 7231).
    """
    response = getattr(error, "response", None)
    if response is None:
        return None
    headers = getattr(response, "headers", None) or {}
    value = None
    if hasattr(headers, "get"):
        value = headers.get("Retry-After") or headers.get("retry-after")
    if value is None:
        return None
    # Numeric seconds
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        pass
    # HTTP-date
    try:
        dt = parsedate_to_datetime(str(value))
        if dt is None:
            return None
        # If naive, treat as UTC-ish epoch compare via time.mktime alternative:
        delay = dt.timestamp() - time.time()
        return max(0.0, delay)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _compute_delay(
    attempt: int,
    *,
    base_delay: float,
    max_delay: float,
    retry_after: Optional[float],
    jitter: float,
    rng: random.Random,
) -> float:
    """Exponential backoff with full jitter, optionally floored by Retry-After."""
    exp = min(max_delay, base_delay * (2 ** max(0, attempt - 1)))
    if retry_after is not None:
        exp = max(exp, retry_after)
    if jitter <= 0:
        return exp
    # Full jitter in [exp * (1 - jitter), exp]
    low = exp * max(0.0, 1.0 - jitter)
    return rng.uniform(low, exp)


def call_with_retry(
    fn: Callable[[], Any],
    *,
    max_attempts: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    max_total_wait: float = 60.0,
    jitter: float = 0.25,
    retryable: Tuple[type, ...] = RETRYABLE_ERRORS,
    sleep_fn: Callable[[float], None] = time.sleep,
    rng: Optional[random.Random] = None,
) -> Any:
    """Call *fn* with exponential backoff + jitter on transient errors.

    Honors ``Retry-After`` (seconds or HTTP-date) when present.
    Caps both per-sleep delay and total wait time so demos never hang forever.
    Also retries HTTP 5xx / selected gateway statuses via APIStatusError.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    if not 0.0 <= jitter <= 1.0:
        raise ValueError("jitter must be in [0, 1]")

    attempt = 0
    waited = 0.0
    last_error: Optional[BaseException] = None
    _rng = rng or random.Random()

    while attempt < max_attempts:
        attempt += 1
        try:
            return fn()
        except retryable as exc:
            last_error = exc
            if attempt >= max_attempts:
                break
            delay = _compute_delay(
                attempt,
                base_delay=base_delay,
                max_delay=max_delay,
                retry_after=parse_retry_after(exc),
                jitter=jitter,
                rng=_rng,
            )
            remaining = max_total_wait - waited
            if remaining <= 0:
                break
            delay = min(delay, remaining)
            sleep_fn(delay)
            waited += delay
        except APIStatusError as exc:
            status = getattr(exc, "status_code", None)
            try:
                status_i = int(status) if status is not None else None
            except (TypeError, ValueError):
                status_i = None
            retriable_status = status_i is not None and (
                status_i in RETRYABLE_STATUS_CODES or 500 <= status_i < 600
            )
            if not retriable_status:
                raise
            last_error = exc
            if attempt >= max_attempts:
                break
            delay = _compute_delay(
                attempt,
                base_delay=base_delay,
                max_delay=max_delay,
                retry_after=parse_retry_after(exc),
                jitter=jitter,
                rng=_rng,
            )
            remaining = max_total_wait - waited
            if remaining <= 0:
                break
            delay = min(delay, remaining)
            sleep_fn(delay)
            waited += delay

    assert last_error is not None
    raise last_error


# ---------------------------------------------------------------------------
# Redaction / safe previews
# ---------------------------------------------------------------------------


def redact_text(text: Optional[str]) -> str:
    """Redact bearer tokens and sk- style keys from free text."""
    if not text:
        return ""
    cleaned = _BEARER_PATTERN.sub("Bearer [redacted]", text)
    cleaned = _SK_PATTERN.sub("sk-[redacted]", cleaned)
    return cleaned


def redacted_preview(text: Optional[str], max_len: int = 80) -> str:
    """Short preview for logs; never echoes secrets."""
    cleaned = redact_text(text)
    if len(cleaned) > max_len:
        return cleaned[: max_len - 3] + "..."
    return cleaned


def redact_data(value: Any) -> Any:
    """Recursively redact sensitive keys and credential-looking strings."""
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            key_l = str(k).lower().replace("-", "_")
            if any(frag in key_l for frag in _SENSITIVE_KEY_FRAGMENTS):
                out[k] = "[redacted]"
            else:
                out[k] = redact_data(v)
        return out
    if isinstance(value, (list, tuple)):
        return [redact_data(v) for v in value]
    return value
