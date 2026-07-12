from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from typing import Any, AsyncIterator, Protocol
from urllib.parse import urlparse

from hy3_code_review_mcp.config import Hy3Settings, load_default_dotenv

from .tools import TOOL_DEFINITIONS, ToolResult, execute_tool_async, list_files


SYSTEM_PROMPT = """You are Hy3 acting as a senior incident investigator.

Build a short visible investigation plan, then gather evidence with the provided tools before drawing conclusions. Cite filenames and line numbers whenever possible. Do not invent file contents, command output, or tool results. Use only the provided tools.

Your final report must be concise Markdown with these sections:
1. Root cause
2. Evidence
3. Remediation
4. Verification
"""

MAX_EMPTY_RESPONSE_RETRIES = 2
MAX_INVESTIGATION_SECONDS = 90
MAX_MODEL_CALL_SECONDS = 30
MAX_TOOL_CALLS = 12
MAX_TOOL_SECONDS = 20
EMPTY_RESPONSE_NUDGE = (
    "Your previous response was empty. Return at least one tool call or a complete "
    "final incident report grounded in the available evidence."
)


@dataclass(frozen=True)
class AgentToolCall:
    id: str
    name: str
    arguments: str


@dataclass(frozen=True)
class AgentMessage:
    content: str | None
    tool_calls: tuple[AgentToolCall, ...]


class AgentChatClient(Protocol):
    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        timeout_seconds: float | None = None,
    ) -> AgentMessage:
        ...


class AgentConfigurationError(RuntimeError):
    pass


class InvestigationDeadlineError(TimeoutError):
    pass


class OpenAIHy3AgentClient:
    def __init__(self, settings: Hy3Settings, sdk_client: Any | None = None):
        self.settings = settings
        if sdk_client is None:
            from openai import AsyncOpenAI

            sdk_client = AsyncOpenAI(
                base_url=settings.base_url,
                api_key=settings.api_key,
                timeout=MAX_MODEL_CALL_SECONDS,
            )
        self.sdk_client = sdk_client

    def _extra_body(self) -> dict[str, Any]:
        effort = self.settings.reasoning_effort
        if not effort:
            return {}
        if "openrouter.ai" in self.settings.base_url:
            mapped = "none" if effort == "no_think" else effort
            return {"reasoning": {"effort": mapped}}
        return {"chat_template_kwargs": {"reasoning_effort": effort}}

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        timeout_seconds: float | None = None,
    ) -> AgentMessage:
        arguments: dict[str, Any] = {
            "model": self.settings.model,
            "messages": messages,
            "temperature": self.settings.temperature,
            "top_p": self.settings.top_p,
            "max_tokens": self.settings.max_tokens,
            "extra_body": self._extra_body(),
        }
        if tools is not None:
            arguments["tools"] = tools
            arguments["tool_choice"] = "auto"
        if timeout_seconds is not None:
            arguments["timeout"] = max(0.1, timeout_seconds)

        response = await self.sdk_client.chat.completions.create(**arguments)
        message = response.choices[0].message
        tool_calls = tuple(
            AgentToolCall(
                id=call.id,
                name=call.function.name,
                arguments=call.function.arguments,
            )
            for call in (message.tool_calls or ())
        )
        return AgentMessage(content=message.content, tool_calls=tool_calls)


def _settings_ready(settings: Hy3Settings) -> bool:
    hostname = (urlparse(settings.base_url).hostname or "").lower()
    is_local = hostname in {"localhost", "127.0.0.1", "::1"}
    has_key = bool(settings.api_key and settings.api_key != "EMPTY")
    return bool(settings.base_url and settings.model and (is_local or has_key))


def get_agent_client() -> OpenAIHy3AgentClient:
    load_default_dotenv()
    settings = Hy3Settings.from_env()
    if not _settings_ready(settings):
        raise AgentConfigurationError(
            "Hy3 API is not configured. Add credentials to .env and retry."
        )
    return OpenAIHy3AgentClient(settings)


def _assistant_payload(message: AgentMessage) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "role": "assistant",
        "content": message.content,
    }
    if message.tool_calls:
        payload["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.name,
                    "arguments": call.arguments,
                },
            }
            for call in message.tool_calls
        ]
    return payload


def _parse_arguments(raw_arguments: str) -> tuple[dict[str, Any] | None, ToolResult | None]:
    try:
        arguments = json.loads(raw_arguments or "{}")
    except json.JSONDecodeError:
        return None, ToolResult(False, "Tool arguments must be valid JSON object.")
    if not isinstance(arguments, dict):
        return None, ToolResult(False, "Tool arguments must be a JSON object.")
    return arguments, None


def _remaining_seconds(deadline: float, maximum: float) -> float:
    remaining = deadline - monotonic()
    if remaining <= 0:
        raise InvestigationDeadlineError
    return min(maximum, remaining)


async def _complete_with_empty_retry(
    client: AgentChatClient,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    deadline: float,
) -> AgentMessage:
    message = AgentMessage(None, ())
    for attempt in range(MAX_EMPTY_RESPONSE_RETRIES + 1):
        message = await client.complete(
            messages,
            tools,
            timeout_seconds=_remaining_seconds(deadline, MAX_MODEL_CALL_SECONDS),
        )
        if message.tool_calls or (message.content or "").strip():
            return message
        if attempt < MAX_EMPTY_RESPONSE_RETRIES:
            messages.append({"role": "user", "content": EMPTY_RESPONSE_NUDGE})
    return message


async def investigate(
    task: str,
    root: Path,
    client: AgentChatClient,
    max_rounds: int = 8,
    max_tool_calls: int = MAX_TOOL_CALLS,
    max_seconds: float = MAX_INVESTIGATION_SECONDS,
) -> AsyncIterator[dict[str, Any]]:
    manifest = list_files(root).content
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Incident task:\n{task}\n\n"
                f"Workspace manifest:\n{manifest}\n\n"
                "Investigate the incident and ground every conclusion in tool evidence."
            ),
        },
    ]
    deadline = monotonic() + max_seconds
    yield {
        "type": "started",
        "max_rounds": max_rounds,
        "max_tool_calls": max_tool_calls,
        "max_seconds": max_seconds,
    }
    plan_emitted = False
    tool_call_count = 0
    tool_limit_reached = False

    try:
        for round_number in range(1, max_rounds + 1):
            message = await _complete_with_empty_retry(
                client,
                messages,
                TOOL_DEFINITIONS,
                deadline,
            )
            messages.append(_assistant_payload(message))

            if not message.tool_calls:
                report = (message.content or "").strip()
                if not report:
                    yield {
                        "type": "error",
                        "message": "Hy3 returned an empty investigation report.",
                    }
                    yield {"type": "done", "status": "error"}
                    return
                yield {"type": "report", "content": report}
                yield {"type": "done", "status": "completed"}
                return

            if message.content and not plan_emitted:
                yield {"type": "plan", "content": message.content.strip()}
                plan_emitted = True

            for call in message.tool_calls:
                tool_call_count += 1
                arguments, parse_error = _parse_arguments(call.arguments)
                display_arguments: Any = arguments if arguments is not None else call.arguments
                yield {
                    "type": "tool_call",
                    "round": round_number,
                    "call_id": call.id,
                    "tool": call.name,
                    "arguments": display_arguments,
                }

                if tool_call_count > max_tool_calls:
                    tool_limit_reached = True
                    result = ToolResult(
                        False,
                        f"Investigation tool call limit reached ({max_tool_calls}).",
                    )
                elif parse_error:
                    result = parse_error
                else:
                    result = await execute_tool_async(
                        root,
                        call.name,
                        arguments or {},
                        timeout_seconds=_remaining_seconds(
                            deadline,
                            MAX_TOOL_SECONDS,
                        ),
                    )
                yield {
                    "type": "tool_result",
                    "round": round_number,
                    "call_id": call.id,
                    "tool": call.name,
                    "ok": result.ok,
                    "content": result.content,
                }
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(
                            {"ok": result.ok, "content": result.content},
                            ensure_ascii=False,
                        ),
                    }
                )

            if tool_limit_reached:
                break

        messages.append(
            {
                "role": "user",
                "content": (
                    "Investigation limit reached. Synthesize the available evidence now. "
                    "Do not request more tools and do not invent missing evidence."
                ),
            }
        )
        final_message = await _complete_with_empty_retry(
            client,
            messages,
            None,
            deadline,
        )
        report = (final_message.content or "").strip()
        if report:
            yield {"type": "report", "content": report}
            yield {"type": "done", "status": "completed"}
        else:
            yield {
                "type": "error",
                "message": "Hy3 returned an empty investigation report.",
            }
            yield {"type": "done", "status": "error"}
    except InvestigationDeadlineError:
        yield {
            "type": "error",
            "message": f"Investigation exceeded the {max_seconds:g}-second deadline.",
        }
        yield {"type": "done", "status": "error"}
    except Exception:
        yield {
            "type": "error",
            "message": "Hy3 investigation failed. Check the API and retry.",
        }
        yield {"type": "done", "status": "error"}
