"""Shared helpers for the Hy3 hosted API examples.

The module keeps network setup, streaming aggregation, tool-loop safety, retry
policy, and output redaction in one place so the six examples stay focused.
"""

from __future__ import annotations

import json
import math
import os
import random
import re
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, TypeVar
from urllib.parse import urlsplit, urlunsplit

DEFAULT_MODEL = "hy3"
RETRIABLE_STATUS_CODES = frozenset({429, 502, 503, 504})
REASONING_EFFORTS = frozenset({"low", "medium", "high"})
_MODEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")
_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "cookie",
        "proxy_authorization",
        "secret",
        "set_cookie",
        "token",
        "x_api_key",
    }
)
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")

T = TypeVar("T")
CompletionCallable = Callable[..., Any]


class ConfigError(ValueError):
    """Raised when required API configuration is missing or unsafe."""


class StreamInterruptedError(RuntimeError):
    """Raised when a stream fails after yielding a potentially useful prefix."""

    def __init__(self, partial: StreamResult) -> None:
        super().__init__("The response stream was interrupted before completion.")
        self.partial = partial


class ToolLoopError(RuntimeError):
    """Base class for controlled tool-loop failures."""


class ToolArgumentsError(ToolLoopError):
    """Raised when model-provided tool arguments are invalid."""


class UnknownToolError(ToolLoopError):
    """Raised when the model requests a tool outside the allowlist."""


class DuplicateToolCallError(ToolLoopError):
    """Raised when the same tool request repeats within one loop."""


class ToolRoundLimitError(ToolLoopError):
    """Raised when the model keeps requesting tools past the configured limit."""


class RetryBudgetExceeded(RuntimeError):
    """Raised when Retry-After/backoff would exceed the total wait budget."""


@dataclass(frozen=True, slots=True)
class ApiConfig:
    """Validated configuration loaded only from environment variables."""

    api_key: str
    base_url: str
    model: str = DEFAULT_MODEL
    timeout_seconds: float = 60.0

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
        *,
        require_api_key: bool = True,
    ) -> ApiConfig:
        source = os.environ if env is None else env
        api_key = source.get("HY3_API_KEY", "").strip()
        if require_api_key and (
            not api_key or api_key.upper() in {"EMPTY", "YOUR_API_KEY", "REPLACE_ME"}
        ):
            raise ConfigError(
                "HY3_API_KEY is not set. Export it locally; never paste it into "
                "source code, logs, screenshots, or chat."
            )

        raw_base_url = source.get("HY3_BASE_URL", "").strip()
        if not raw_base_url:
            raise ConfigError(
                "HY3_BASE_URL is not set. Use the /v1 endpoint for TokenHub or "
                "the documented /plan/v3 endpoint for Token Plan."
            )
        base_url = normalize_base_url(raw_base_url)

        model = source.get("HY3_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
        if not _MODEL_PATTERN.fullmatch(model):
            raise ConfigError("HY3_MODEL contains unsupported characters.")

        raw_timeout = source.get("HY3_TIMEOUT_SECONDS", "60").strip()
        try:
            timeout_seconds = float(raw_timeout)
        except ValueError as exc:
            raise ConfigError("HY3_TIMEOUT_SECONDS must be a number.") from exc
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ConfigError("HY3_TIMEOUT_SECONDS must be a positive finite number.")

        return cls(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout_seconds=timeout_seconds,
        )


def normalize_base_url(raw_url: str) -> str:
    """Validate a documented OpenAI-compatible base URL without guessing paths."""

    parsed = urlsplit(raw_url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ConfigError("HY3_BASE_URL must be an absolute http(s) URL.")
    if parsed.username or parsed.password:
        raise ConfigError("HY3_BASE_URL must not contain credentials.")
    if parsed.query or parsed.fragment:
        raise ConfigError("HY3_BASE_URL must not contain a query string or fragment.")
    if parsed.scheme == "http" and parsed.hostname not in {
        "127.0.0.1",
        "localhost",
        "::1",
    }:
        raise ConfigError("Remote HY3_BASE_URL values must use HTTPS.")

    path = parsed.path.rstrip("/")
    if path not in {"/v1", "/plan/v3"}:
        raise ConfigError(
            "HY3_BASE_URL must end at /v1 or /plan/v3, not at "
            "/chat/completions or another resource path."
        )
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def create_client(config: ApiConfig) -> Any:
    """Create an OpenAI client with SDK retries disabled for explicit examples."""

    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - depends on the user's environment
        raise ConfigError(
            "The openai package is missing. Run: "
            "python -m pip install -r examples/api/requirements.txt"
        ) from exc
    return OpenAI(
        api_key=config.api_key,
        base_url=config.base_url,
        timeout=config.timeout_seconds,
        max_retries=0,
    )


def thinking_body(enabled: bool, effort: str | None = None) -> dict[str, Any]:
    """Build TokenHub's top-level thinking fields for OpenAI SDK extra_body."""

    if effort is not None and effort not in REASONING_EFFORTS:
        choices = ", ".join(sorted(REASONING_EFFORTS))
        raise ValueError(f"reasoning effort must be one of: {choices}")
    if not enabled and effort is not None:
        raise ValueError("reasoning effort cannot be set when thinking is disabled")

    body: dict[str, Any] = {"thinking": {"type": "enabled" if enabled else "disabled"}}
    if effort is not None:
        body["reasoning_effort"] = effort
    return body


def get_field(value: Any, name: str, default: Any = None) -> Any:
    """Read a field from either SDK objects or plain dictionaries."""

    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def to_plain(value: Any) -> Any:
    """Convert SDK/Pydantic objects into JSON-compatible Python containers."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(key): to_plain(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [to_plain(item) for item in value]
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return to_plain(model_dump(exclude_none=True))
    if hasattr(value, "__dict__"):
        return {
            str(key): to_plain(item)
            for key, item in vars(value).items()
            if not key.startswith("_") and item is not None
        }
    return str(value)


def _normalise_sensitive_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")


def redact_data(value: Any, *, secrets: Iterable[str] = ()) -> Any:
    """Recursively remove credential fields and redact bearer/known secret values."""

    known_secrets = tuple(secret for secret in secrets if secret)
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            string_key = str(key)
            normalised = _normalise_sensitive_key(string_key)
            if normalised in _SENSITIVE_KEYS or normalised.endswith("_api_key"):
                redacted[string_key] = "***REDACTED***"
            else:
                redacted[string_key] = redact_data(item, secrets=known_secrets)
        return redacted
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [redact_data(item, secrets=known_secrets) for item in value]
    if isinstance(value, str):
        result = _BEARER_PATTERN.sub("Bearer ***REDACTED***", value)
        for secret in known_secrets:
            result = result.replace(secret, "***REDACTED***")
        return result
    return value


def response_summary(response: Any, *, secrets: Iterable[str] = ()) -> dict[str, Any]:
    """Return useful response fields while excluding request IDs and headers."""

    choices = get_field(response, "choices", []) or []
    choice = choices[0] if choices else None
    message = get_field(choice, "message") if choice is not None else None
    summary: dict[str, Any] = {
        "model": get_field(response, "model"),
        "finish_reason": get_field(choice, "finish_reason") if choice else None,
        "message": {
            "role": get_field(message, "role"),
            "reasoning_content": get_field(message, "reasoning_content"),
            "content": get_field(message, "content"),
            "tool_calls": to_plain(get_field(message, "tool_calls")),
        },
        "usage": to_plain(get_field(response, "usage")),
    }
    return redact_data(summary, secrets=secrets)


def print_response(response: Any, *, secrets: Iterable[str] = ()) -> None:
    """Print a stable, redacted response summary as UTF-8 JSON."""

    print(
        json.dumps(
            response_summary(response, secrets=secrets), ensure_ascii=False, indent=2
        )
    )


def safe_error_message(error: BaseException) -> str:
    """Describe a failure without exposing exception bodies, headers, or request IDs."""

    if isinstance(error, ConfigError):
        return f"Configuration error: {error}"
    if isinstance(error, (ToolLoopError, RetryBudgetExceeded)):
        return f"Example stopped safely: {error}"
    status = status_code_from_error(error)
    if status is not None:
        return (
            f"API request failed with HTTP {status}. Response details were omitted; "
            "see quickstart.md for troubleshooting."
        )
    if is_retryable_error(error):
        return (
            f"API request failed with {error.__class__.__name__}. Details were omitted "
            "to avoid leaking request metadata."
        )
    return (
        f"Example failed with {error.__class__.__name__}. Details were omitted to avoid "
        "leaking request metadata."
    )


def run_example(main: Callable[[], None]) -> None:
    """Run an example with a consistent, non-sensitive top-level error boundary."""

    try:
        main()
    except Exception as exc:
        raise SystemExit(safe_error_message(exc)) from None


@dataclass(frozen=True, slots=True)
class ToolCallData:
    index: int
    id: str | None
    type: str
    name: str | None
    arguments: str


@dataclass(frozen=True, slots=True)
class StreamResult:
    content: str
    reasoning_content: str
    tool_calls: tuple[ToolCallData, ...]
    finish_reason: str | None
    usage: Any
    complete: bool


@dataclass(slots=True)
class _ToolCallBuffer:
    index: int
    id: str | None = None
    type: str = "function"
    name: str | None = None
    argument_parts: list[str] = field(default_factory=list)


def _stream_result(
    content_parts: list[str],
    reasoning_parts: list[str],
    tool_buffers: Mapping[int, _ToolCallBuffer],
    finish_reason: str | None,
    usage: Any,
    *,
    complete: bool,
) -> StreamResult:
    tool_calls = tuple(
        ToolCallData(
            index=buffer.index,
            id=buffer.id,
            type=buffer.type,
            name=buffer.name,
            arguments="".join(buffer.argument_parts),
        )
        for _, buffer in sorted(tool_buffers.items())
    )
    return StreamResult(
        content="".join(content_parts),
        reasoning_content="".join(reasoning_parts),
        tool_calls=tool_calls,
        finish_reason=finish_reason,
        usage=to_plain(usage),
        complete=complete,
    )


def aggregate_stream(
    chunks: Iterable[Any],
    *,
    on_content: Callable[[str], None] | None = None,
    on_reasoning: Callable[[str], None] | None = None,
) -> StreamResult:
    """Aggregate content, reasoning, tool fragments, finish reason, and usage."""

    content_parts: list[str] = []
    reasoning_parts: list[str] = []
    tool_buffers: dict[int, _ToolCallBuffer] = {}
    finish_reason: str | None = None
    usage: Any = None

    iterator = iter(chunks)
    while True:
        try:
            chunk = next(iterator)
        except StopIteration:
            break
        except Exception as exc:
            partial = _stream_result(
                content_parts,
                reasoning_parts,
                tool_buffers,
                finish_reason,
                usage,
                complete=False,
            )
            raise StreamInterruptedError(partial) from exc

        chunk_usage = get_field(chunk, "usage")
        if chunk_usage is not None:
            usage = chunk_usage

        choices = get_field(chunk, "choices", []) or []
        if not choices:  # Includes the usage-only tail chunk.
            continue
        choice = choices[0]
        finish_reason = get_field(choice, "finish_reason") or finish_reason
        delta = get_field(choice, "delta")
        if delta is None:
            continue

        reasoning = get_field(delta, "reasoning_content")
        if reasoning:
            reasoning_parts.append(reasoning)
            if on_reasoning is not None:
                on_reasoning(reasoning)

        content = get_field(delta, "content")
        if content:
            content_parts.append(content)
            if on_content is not None:
                on_content(content)

        for fallback_index, fragment in enumerate(
            get_field(delta, "tool_calls", []) or []
        ):
            raw_index = get_field(fragment, "index", fallback_index)
            index = fallback_index if raw_index is None else int(raw_index)
            buffer = tool_buffers.setdefault(index, _ToolCallBuffer(index=index))
            fragment_id = get_field(fragment, "id")
            if fragment_id:
                buffer.id = fragment_id
            fragment_type = get_field(fragment, "type")
            if fragment_type:
                buffer.type = fragment_type
            function = get_field(fragment, "function")
            if function is not None:
                name = get_field(function, "name")
                if name:
                    buffer.name = name
                arguments = get_field(function, "arguments")
                if arguments:
                    buffer.argument_parts.append(arguments)

    return _stream_result(
        content_parts,
        reasoning_parts,
        tool_buffers,
        finish_reason,
        usage,
        complete=finish_reason is not None,
    )


def assistant_message_dict(message: Any) -> dict[str, Any]:
    """Serialize an assistant message, preserving reasoning beside tool calls."""

    result: dict[str, Any] = {
        "role": get_field(message, "role", "assistant") or "assistant",
        "content": get_field(message, "content") or "",
    }
    reasoning = get_field(message, "reasoning_content")
    if reasoning is not None:
        result["reasoning_content"] = reasoning
    tool_calls = get_field(message, "tool_calls")
    if tool_calls:
        result["tool_calls"] = to_plain(tool_calls)
    return result


def _schemas_from_tools(
    tools: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    schemas: dict[str, Mapping[str, Any]] = {}
    for tool in tools:
        function = tool.get("function", {})
        name = function.get("name")
        parameters = function.get("parameters")
        if isinstance(name, str) and isinstance(parameters, Mapping):
            schemas[name] = parameters
    return schemas


def _parse_and_validate_arguments(
    name: str,
    raw_arguments: str,
    schemas: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    try:
        arguments = json.loads(raw_arguments)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ToolArgumentsError(
            f"Tool {name!r} returned invalid JSON arguments."
        ) from exc
    if not isinstance(arguments, dict):
        raise ToolArgumentsError(f"Tool {name!r} arguments must be a JSON object.")

    schema = schemas.get(name)
    if schema is not None:
        try:
            from jsonschema import ValidationError, validate

            validate(arguments, schema)
        except ImportError as exc:  # pragma: no cover - dependency error in user env
            raise ToolLoopError(
                "jsonschema is required for tool argument validation."
            ) from exc
        except ValidationError as exc:
            raise ToolArgumentsError(
                f"Tool {name!r} arguments do not match its JSON Schema."
            ) from exc
    return arguments


@dataclass(frozen=True, slots=True)
class ToolLoopResult:
    response: Any
    messages: tuple[dict[str, Any], ...]
    tool_rounds: int


def run_tool_loop(
    create_completion: CompletionCallable,
    *,
    messages: Sequence[Mapping[str, Any]],
    tools: Sequence[Mapping[str, Any]],
    handlers: Mapping[str, Callable[..., Any]],
    request_kwargs: Mapping[str, Any],
    max_tool_rounds: int = 4,
    on_response: Callable[[int, Any], None] | None = None,
) -> ToolLoopResult:
    """Run a bounded allowlisted tool loop with schema and repeat protection."""

    if max_tool_rounds < 1:
        raise ValueError("max_tool_rounds must be at least 1")
    if "messages" in request_kwargs or "tools" in request_kwargs:
        raise ValueError("request_kwargs must not override messages or tools")

    history = [dict(message) for message in messages]
    schemas = _schemas_from_tools(tools)
    seen_ids: set[str] = set()
    seen_signatures: set[tuple[str, str]] = set()

    for round_index in range(max_tool_rounds + 1):
        response = create_completion(
            messages=history,
            tools=list(tools),
            **dict(request_kwargs),
        )
        if on_response is not None:
            on_response(round_index, response)

        choices = get_field(response, "choices", []) or []
        if not choices:
            raise ToolLoopError("The model response contains no choices.")
        message = get_field(choices[0], "message")
        tool_calls = get_field(message, "tool_calls", []) or []
        if not tool_calls:
            history.append(assistant_message_dict(message))
            return ToolLoopResult(
                response=response,
                messages=tuple(history),
                tool_rounds=round_index,
            )
        if round_index >= max_tool_rounds:
            raise ToolRoundLimitError(
                f"Model requested tools after {max_tool_rounds} allowed tool rounds."
            )

        history.append(assistant_message_dict(message))
        for tool_call in tool_calls:
            call_id = str(get_field(tool_call, "id", "")).strip()
            function = get_field(tool_call, "function")
            name = str(get_field(function, "name", "")).strip()
            raw_arguments = get_field(function, "arguments", "")
            if not call_id or not name:
                raise ToolLoopError(
                    "Tool calls must include both id and function name."
                )
            if name not in handlers:
                raise UnknownToolError(f"Model requested unknown tool {name!r}.")

            arguments = _parse_and_validate_arguments(name, raw_arguments, schemas)
            canonical_arguments = json.dumps(
                arguments, sort_keys=True, separators=(",", ":")
            )
            signature = (name, canonical_arguments)
            if call_id in seen_ids or signature in seen_signatures:
                raise DuplicateToolCallError(
                    f"Repeated tool invocation blocked for {name!r}."
                )
            seen_ids.add(call_id)
            seen_signatures.add(signature)

            try:
                result = handlers[name](**arguments)
            except Exception as exc:
                raise ToolLoopError(f"Allowlisted tool {name!r} failed.") from exc
            tool_content = (
                result
                if isinstance(result, str)
                else json.dumps(result, ensure_ascii=False, sort_keys=True)
            )
            history.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": tool_content,
                }
            )

    raise AssertionError("unreachable")


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 4
    base_delay: float = 0.5
    max_delay: float = 8.0
    max_total_wait: float = 20.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.base_delay < 0 or self.max_delay < 0 or self.max_total_wait < 0:
            raise ValueError("retry delays must be non-negative")


def status_code_from_error(error: BaseException) -> int | None:
    """Read an HTTP status from OpenAI-style exceptions without importing SDK types."""

    status = getattr(error, "status_code", None)
    if status is None:
        response = getattr(error, "response", None)
        status = getattr(response, "status_code", None)
    try:
        return int(status) if status is not None else None
    except (TypeError, ValueError):
        return None


def is_retryable_error(error: BaseException) -> bool:
    """Retry only documented transient HTTP/network/timeout failures."""

    status = status_code_from_error(error)
    if status is not None:
        return status in RETRIABLE_STATUS_CODES
    if isinstance(error, (TimeoutError, ConnectionError)):
        return True
    return error.__class__.__name__ in {"APIConnectionError", "APITimeoutError"}


def retry_after_seconds(
    error: BaseException,
    *,
    now: datetime | None = None,
) -> float | None:
    """Parse Retry-After seconds or an HTTP date from an exception response."""

    response = getattr(error, "response", None)
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    raw_value = headers.get("Retry-After") or headers.get("retry-after")
    if raw_value is None:
        return None
    try:
        seconds = float(raw_value)
        return max(0.0, seconds) if math.isfinite(seconds) else None
    except (TypeError, ValueError):
        pass

    try:
        retry_at = parsedate_to_datetime(str(raw_value))
    except (TypeError, ValueError, OverflowError):
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    return max(0.0, (retry_at - current).total_seconds())


def _backoff_delay(attempt: int, policy: RetryPolicy, random_value: float) -> float:
    exponential = min(policy.max_delay, policy.base_delay * (2 ** (attempt - 1)))
    bounded_random = min(1.0, max(0.0, random_value))
    return exponential * (0.5 + 0.5 * bounded_random)


def call_with_retry(
    operation: Callable[[], T],
    *,
    policy: RetryPolicy = RetryPolicy(),
    sleep: Callable[[float], None] = time.sleep,
    random_fn: Callable[[], float] = random.random,
    on_retry: Callable[[int, BaseException, float], None] | None = None,
) -> T:
    """Call an operation with bounded retry, Retry-After, and equal jitter."""

    total_wait = 0.0
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return operation()
        except Exception as exc:
            if not is_retryable_error(exc) or attempt >= policy.max_attempts:
                raise

            retry_after = retry_after_seconds(exc)
            delay = (
                retry_after
                if retry_after is not None
                else _backoff_delay(attempt, policy, random_fn())
            )
            if total_wait + delay > policy.max_total_wait:
                raise RetryBudgetExceeded(
                    "Retry wait budget exhausted before the next attempt."
                ) from exc
            if on_retry is not None:
                on_retry(attempt, exc, delay)
            sleep(delay)
            total_wait += delay

    raise AssertionError("unreachable")


def create_chat_completion(
    client: Any,
    *,
    policy: RetryPolicy = RetryPolicy(),
    on_retry: Callable[[int, BaseException, float], None] | None = None,
    **request: Any,
) -> Any:
    """Create a chat completion with the examples' bounded retry policy."""

    return call_with_retry(
        lambda: client.chat.completions.create(**request),
        policy=policy,
        on_retry=on_retry,
    )
