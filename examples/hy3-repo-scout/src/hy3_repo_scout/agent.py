"""Bounded multi-round repository investigation loop for Hy3."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .citations import EvidenceLine
from .client import create_chat_completion, create_client
from .config import Settings
from .prompts import SYSTEM_PROMPT, build_user_prompt

AgentEvent = dict[str, Any]
EventCallback = Callable[[AgentEvent], None]


class AgentProtocolError(RuntimeError):
    """Raised when a model response does not follow Chat Completions format."""


@dataclass(frozen=True, slots=True)
class ToolTrace:
    """One requested tool call and the bounded result returned to the model."""

    round: int
    call_id: str
    name: str
    arguments: dict[str, Any]
    result: str
    error: str | None = None
    truncated: bool = False
    context_chars: int = 0
    evidence: tuple[EvidenceLine, ...] = field(default=(), repr=False)


ReportValidator = Callable[[str, tuple[ToolTrace, ...]], Mapping[str, Any]]


@dataclass(frozen=True, slots=True)
class AgentResult:
    """Final report plus reproducible investigation statistics."""

    content: str
    rounds: int
    tool_calls: int
    files_read: int
    context_chars: int
    usage: dict[str, int]
    trace: tuple[ToolTrace, ...] = field(default=(), repr=False)
    messages: tuple[dict[str, Any], ...] = field(default=(), repr=False)
    file_paths: tuple[str, ...] = field(default=(), repr=False)
    finish_reason: str | None = None
    budget_exhausted: bool = False

    @property
    def tool_trace(self) -> tuple[ToolTrace, ...]:
        """Descriptive alias used by renderers and JSON consumers."""

        return self.trace

    def to_dict(self) -> dict[str, Any]:
        """Return a bounded JSON-safe summary that omits prompts and tool contents."""

        return {
            "content": self.content,
            "rounds": self.rounds,
            "tool_calls": self.tool_calls,
            "files_read": self.files_read,
            "context_chars": self.context_chars,
            "usage": dict(self.usage),
            "file_paths": list(self.file_paths),
            "finish_reason": self.finish_reason,
            "budget_exhausted": self.budget_exhausted,
        }


@dataclass(frozen=True, slots=True)
class _RequestedTool:
    call_id: str
    name: str
    raw_arguments: str
    wire: dict[str, Any]


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _text_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, Sequence) and not isinstance(content, (bytes, bytearray)):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
                continue
            text = _field(part, "text")
            if isinstance(text, str):
                parts.append(text)
        if parts:
            return "".join(parts)
    return str(content)


def _json_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _usage(response: Any) -> dict[str, int]:
    raw = _field(response, "usage")
    result: dict[str, int] = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }
    if raw is None:
        return result
    for key in result:
        value = _field(raw, key, 0)
        if isinstance(value, int) and not isinstance(value, bool):
            result[key] = value
    if not result["total_tokens"]:
        result["total_tokens"] = (
            result["prompt_tokens"] + result["completion_tokens"]
        )
    return result


def _add_usage(total: dict[str, int], current: Mapping[str, int]) -> None:
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        total[key] = total.get(key, 0) + int(current.get(key, 0))


def _tool_schemas(tools: Any) -> list[Mapping[str, Any]]:
    for name in ("schemas", "tool_schemas"):
        value = getattr(tools, name, None)
        if value is not None:
            value = value() if callable(value) else value
            return list(value)
    getter = getattr(tools, "get_schemas", None)
    if callable(getter):
        return list(getter())
    value = getattr(tools, "TOOL_SCHEMAS", None)
    return list(value) if value is not None else []


def _repo_summary(tools: Any) -> str:
    for name in ("repo_summary", "summary"):
        value = getattr(tools, name, None)
        if value is not None:
            value = value() if callable(value) else value
            if value:
                return str(value)
    root = getattr(tools, "root", None) or getattr(tools, "repo_root", None)
    if root is not None:
        return f"Read-only repository named {Path(str(root)).name!r}."
    return "A read-only repository is available through the supplied tools."


def _parse_tool_calls(message: Any, round_number: int) -> list[_RequestedTool]:
    raw_calls = _field(message, "tool_calls") or []
    calls: list[_RequestedTool] = []
    for index, call in enumerate(raw_calls, start=1):
        function = _field(call, "function", {})
        name = str(_field(function, "name", ""))
        arguments = _field(function, "arguments", "{}")
        raw_arguments = arguments if isinstance(arguments, str) else _json_text(arguments)
        call_id = str(_field(call, "id", "") or f"call_{round_number}_{index}")
        calls.append(
            _RequestedTool(
                call_id=call_id,
                name=name,
                raw_arguments=raw_arguments,
                wire={
                    "id": call_id,
                    "type": "function",
                    "function": {"name": name, "arguments": raw_arguments},
                },
            )
        )
    return calls


def _assistant_message(message: Any, calls: Sequence[_RequestedTool]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "role": "assistant",
        "content": _text_content(_field(message, "content")) or None,
    }
    dumped: Mapping[str, Any] = message if isinstance(message, Mapping) else {}
    model_dump = getattr(message, "model_dump", None)
    if callable(model_dump):
        candidate = model_dump(exclude_none=True)
        if isinstance(candidate, Mapping):
            dumped = candidate
    for name in ("reasoning", "reasoning_content", "reasoning_details"):
        value = dumped.get(name, _field(message, name))
        if value is not None:
            result[name] = value
    if calls:
        result["tool_calls"] = [call.wire for call in calls]
    return result


def _parse_arguments(raw: str) -> dict[str, Any]:
    try:
        arguments = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"tool arguments are not valid JSON: {exc.msg}") from exc
    if not isinstance(arguments, dict):
        raise ValueError("tool arguments must be a JSON object")
    return arguments


def _structured_error(code: str, message: str) -> dict[str, Any]:
    return {"error": {"code": code, "message": message}}


def _result_error(value: Any) -> str | None:
    if not isinstance(value, Mapping) or "error" not in value:
        return None
    error = value["error"]
    if isinstance(error, Mapping):
        return str(error.get("message") or _json_text(error))
    return str(error)


def _file_stats(observed: set[str]) -> tuple[int, tuple[str, ...]]:
    paths = tuple(sorted(observed))
    return len(paths), paths


def _separate_evidence(value: Any) -> tuple[Any, tuple[EvidenceLine, ...]]:
    if not isinstance(value, Mapping):
        return value, ()
    public = dict(value)
    raw_evidence = public.pop("_evidence", ())
    evidence: list[EvidenceLine] = []
    if isinstance(raw_evidence, Sequence) and not isinstance(raw_evidence, (str, bytes)):
        for item in raw_evidence:
            if not isinstance(item, Mapping):
                continue
            path = item.get("path")
            line = item.get("line")
            digest = item.get("sha256")
            valid_digest = isinstance(digest, str) and len(digest) == 64 and all(
                character in "0123456789abcdef" for character in digest
            )
            if (
                isinstance(path, str)
                and isinstance(line, int)
                and not isinstance(line, bool)
                and line > 0
                and valid_digest
            ):
                evidence.append(EvidenceLine(path=path, line=line, sha256=digest))
    return public, tuple(evidence)


class RepoScoutAgent:
    """Drive Hy3 through a read-only tool loop with hard local budgets."""

    def __init__(
        self,
        settings: Settings,
        tools: Any,
        client: Any | None = None,
        on_event: EventCallback | None = None,
        report_validator: ReportValidator | None = None,
    ) -> None:
        self.settings = settings
        self.tools = tools
        self.client = create_client(settings) if client is None else client
        self.on_event = on_event
        self.report_validator = report_validator
        self.last_report_validation: Mapping[str, Any] | None = None

    def _emit(self, event_type: str, **fields: Any) -> None:
        if self.on_event is not None:
            self.on_event({"type": event_type, **fields})

    def _retry_event(
        self, round_number: int
    ) -> Callable[[Exception, int, float], None]:
        def notify(error: Exception, attempt: int, delay: float) -> None:
            self._emit(
                "retry",
                round=round_number,
                attempt=attempt,
                delay=delay,
                error=type(error).__name__,
            )

        return notify

    def run(self, question: str) -> AgentResult:
        """Investigate a question and always return a bounded final result."""

        if not isinstance(question, str) or not question.strip():
            raise ValueError("question must not be empty")

        settings = self.settings
        schemas = _tool_schemas(self.tools)
        budgets = {
            "model rounds": settings.max_rounds,
            "tool calls": settings.max_tool_calls,
            "repository context characters": settings.max_context_chars,
            "characters per tool result": settings.max_tool_result_chars,
        }
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": build_user_prompt(
                    question, _repo_summary(self.tools), budgets
                ),
            },
        ]
        usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        trace: list[ToolTrace] = []
        observed_files: set[str] = set()
        context_chars = 0
        tool_calls = 0
        last_content = ""
        finish_reason: str | None = None
        budget_exhausted = False
        synthesis_started = False
        repair_attempted = False
        rounds_completed = 0
        self.last_report_validation = None

        for round_number in range(1, settings.max_rounds + 1):
            final_synthesis = synthesis_started or round_number >= max(
                1, settings.max_rounds - 1
            )
            if final_synthesis and not synthesis_started:
                synthesis_started = True
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "This is the final synthesis round. No more tools are available. "
                            "Write the complete cited Markdown report now using only the evidence "
                            "already collected. State any remaining unknowns explicitly."
                        ),
                    }
                )
            self._emit(
                "model_request",
                round=round_number,
                final_synthesis=final_synthesis,
                message_count=len(messages),
                remaining_tool_calls=max(0, settings.max_tool_calls - tool_calls),
                remaining_context_chars=max(
                    0, settings.max_context_chars - context_chars
                ),
            )
            response = create_chat_completion(
                self.client,
                settings,
                messages,
                None if final_synthesis else schemas,
                on_retry=self._retry_event(round_number),
            )
            rounds_completed = round_number
            choices = _field(response, "choices")
            if not choices:
                raise AgentProtocolError("chat completion response has no choices")
            choice = choices[0]
            message = _field(choice, "message")
            if message is None:
                raise AgentProtocolError("chat completion choice has no message")

            round_usage = _usage(response)
            _add_usage(usage, round_usage)
            finish_reason = _field(choice, "finish_reason")
            requested = _parse_tool_calls(message, round_number)
            last_content = _text_content(_field(message, "content"))
            messages.append(_assistant_message(message, requested))
            self._emit(
                "model_response",
                round=round_number,
                finish_reason=finish_reason,
                tool_calls=len(requested),
                usage=round_usage,
            )

            if not requested:
                files_read, file_paths = _file_stats(observed_files)
                result = AgentResult(
                    content=last_content,
                    rounds=round_number,
                    tool_calls=tool_calls,
                    files_read=files_read,
                    context_chars=context_chars,
                    usage=usage,
                    trace=tuple(trace),
                    messages=tuple(messages),
                    file_paths=file_paths,
                    finish_reason=finish_reason,
                    budget_exhausted=budget_exhausted,
                )
                validation: Mapping[str, Any] | None = None
                if self.report_validator is not None:
                    try:
                        validation = self.report_validator(result.content, result.trace)
                    except Exception:
                        validation = {
                            "valid": False,
                            "error": {"code": "validation_failure"},
                        }
                self.last_report_validation = validation
                if (
                    validation is not None
                    and not validation.get("valid")
                    and not repair_attempted
                    and round_number < settings.max_rounds
                ):
                    raw_error = validation.get("error")
                    error = raw_error if isinstance(raw_error, Mapping) else {}
                    code = str(error.get("code") or "invalid_report")[:80]
                    citation = str(error.get("citation") or "")[:300]
                    citation_detail = f" Rejected citation: {citation}." if citation else ""
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "Local citation validation rejected the draft with error code "
                                f"{code}.{citation_detail} Rewrite the complete report now using "
                                "only evidence already present in the tool messages. Every "
                                "citation "
                                "must be its own exact [relative/path:Lstart-Lend] bracket. Repeat "
                                "the full path and both L markers for every range; never use comma "
                                "or semicolon lists, shorthand paths, tool names, or merged search "
                                "matches inside a citation."
                            ),
                        }
                    )
                    synthesis_started = True
                    repair_attempted = True
                    self._emit(
                        "report_repair",
                        round=round_number,
                        error_code=code,
                    )
                    continue
                self._emit(
                    "completed",
                    rounds=result.rounds,
                    tool_calls=result.tool_calls,
                    files_read=result.files_read,
                    context_chars=result.context_chars,
                    usage=dict(result.usage),
                    finish_reason=result.finish_reason,
                    budget_exhausted=result.budget_exhausted,
                )
                return result

            if final_synthesis:
                budget_exhausted = True
                finish_reason = "invalid_final_tool_request"
                last_content = last_content.strip() or (
                    "The model requested another tool during the final synthesis round, so no "
                    "complete report was produced."
                )
                break

            for call in requested:
                if tool_calls >= settings.max_tool_calls:
                    budget_exhausted = True
                    synthesis_started = True
                    error = "tool-call budget exhausted"
                    content = _json_text(_structured_error("tool_budget", error))
                    messages.append(
                        {"role": "tool", "tool_call_id": call.call_id, "content": content}
                    )
                    trace.append(
                        ToolTrace(
                            round=round_number,
                            call_id=call.call_id,
                            name=call.name,
                            arguments={},
                            result=content,
                            error=error,
                        )
                    )
                    self._emit(
                        "tool_end",
                        round=round_number,
                        call_id=call.call_id,
                        name=call.name,
                        error=error,
                        truncated=False,
                        context_chars=0,
                    )
                    continue

                if context_chars >= settings.max_context_chars:
                    budget_exhausted = True
                    synthesis_started = True
                    error = "repository context budget exhausted"
                    content = _json_text(_structured_error("context_budget", error))
                    messages.append(
                        {"role": "tool", "tool_call_id": call.call_id, "content": content}
                    )
                    trace.append(
                        ToolTrace(
                            round=round_number,
                            call_id=call.call_id,
                            name=call.name,
                            arguments={},
                            result=content,
                            error=error,
                        )
                    )
                    self._emit(
                        "tool_end",
                        round=round_number,
                        call_id=call.call_id,
                        name=call.name,
                        error=error,
                        truncated=False,
                        context_chars=0,
                    )
                    continue

                tool_calls += 1
                try:
                    arguments = _parse_arguments(call.raw_arguments)
                except ValueError as exc:
                    arguments = {"_raw": call.raw_arguments}
                    error = str(exc)
                    value: Any = _structured_error("invalid_arguments", error)
                else:
                    self._emit(
                        "tool_start",
                        round=round_number,
                        call_id=call.call_id,
                        name=call.name,
                        arguments=dict(arguments),
                    )
                    executor = getattr(self.tools, "execute", None)
                    if not callable(executor):
                        error = "tool provider does not expose execute(name, arguments)"
                        value = _structured_error("tool_provider", error)
                    else:
                        try:
                            value = executor(call.name, arguments)
                            error = _result_error(value)
                        except Exception:
                            error = "tool execution failed unexpectedly"
                            value = _structured_error("tool_failure", error)

                value, tool_evidence = _separate_evidence(value)
                serialized = _json_text(value)
                chars_added = 0
                truncated = False
                if error is None:
                    remaining = max(0, settings.max_context_chars - context_chars)
                    if len(serialized) > settings.max_tool_result_chars:
                        error = (
                            "tool result exceeded the per-call context limit; request a smaller "
                            "path, range, or result limit"
                        )
                        serialized = _json_text(
                            _structured_error("tool_result_too_large", error)
                        )
                        truncated = True
                        tool_evidence = ()
                    elif len(serialized) > remaining:
                        budget_exhausted = True
                        synthesis_started = True
                        error = "repository context budget exhausted"
                        serialized = _json_text(
                            _structured_error("context_budget", error)
                        )
                        truncated = True
                        context_chars = settings.max_context_chars
                        tool_evidence = ()
                    else:
                        chars_added = len(serialized)
                        context_chars += chars_added
                        if call.name == "read_file":
                            result_path = _field(value, "path")
                            path = result_path or arguments.get("path")
                            if path:
                                observed_files.add(str(path))
                else:
                    tool_evidence = ()
                    error_limit = min(settings.max_tool_result_chars, 4_096)
                    if len(serialized) > error_limit:
                        serialized = _json_text(
                            _structured_error(
                                "tool_error_too_large",
                                "Tool failed with an oversized error response.",
                            )
                        )
                        truncated = True

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.call_id,
                        "content": serialized,
                    }
                )
                trace.append(
                    ToolTrace(
                        round=round_number,
                        call_id=call.call_id,
                        name=call.name,
                        arguments=dict(arguments),
                        result=serialized,
                        error=error,
                        truncated=truncated,
                        context_chars=chars_added,
                        evidence=tool_evidence,
                    )
                )
                self._emit(
                    "tool_end",
                    round=round_number,
                    call_id=call.call_id,
                    name=call.name,
                    error=error,
                    truncated=truncated,
                    context_chars=chars_added,
                )

        budget_exhausted = True
        files_read, file_paths = _file_stats(observed_files)
        content = last_content.strip() or (
            "The investigation stopped before a final report because the model-round "
            "budget was exhausted."
        )
        result = AgentResult(
            content=content,
            rounds=rounds_completed,
            tool_calls=tool_calls,
            files_read=files_read,
            context_chars=context_chars,
            usage=usage,
            trace=tuple(trace),
            messages=tuple(messages),
            file_paths=file_paths,
            finish_reason=finish_reason or "max_rounds",
            budget_exhausted=budget_exhausted,
        )
        self._emit(
            "completed",
            rounds=result.rounds,
            tool_calls=result.tool_calls,
            files_read=result.files_read,
            context_chars=result.context_chars,
            usage=dict(result.usage),
            finish_reason=result.finish_reason,
            budget_exhausted=result.budget_exhausted,
        )
        return result
