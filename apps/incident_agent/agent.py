from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Protocol
from urllib.parse import urlparse

from hy3_code_review_mcp.config import Hy3Settings, load_default_dotenv

from .tools import TOOL_DEFINITIONS, ToolResult, execute_tool, list_files


SYSTEM_PROMPT = """You are Hy3 acting as a senior incident investigator.

Build a short visible investigation plan, then gather evidence with the provided tools before drawing conclusions. Cite filenames and line numbers whenever possible. Do not invent file contents, command output, or tool results. Use only the provided tools.

Your final report must be concise Markdown with these sections:
1. Root cause
2. Evidence
3. Remediation
4. Verification
"""

MAX_EMPTY_RESPONSE_RETRIES = 2
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
    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AgentMessage:
        ...


class AgentConfigurationError(RuntimeError):
    pass


class OpenAIHy3AgentClient:
    def __init__(self, settings: Hy3Settings, sdk_client: Any | None = None):
        self.settings = settings
        if sdk_client is None:
            from openai import OpenAI

            sdk_client = OpenAI(
                base_url=settings.base_url,
                api_key=settings.api_key,
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

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
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

        response = self.sdk_client.chat.completions.create(**arguments)
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


def _complete_with_empty_retry(
    client: AgentChatClient,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
) -> AgentMessage:
    message = AgentMessage(None, ())
    for attempt in range(MAX_EMPTY_RESPONSE_RETRIES + 1):
        message = client.complete(messages, tools)
        if message.tool_calls or (message.content or "").strip():
            return message
        if attempt < MAX_EMPTY_RESPONSE_RETRIES:
            messages.append({"role": "user", "content": EMPTY_RESPONSE_NUDGE})
    return message


def investigate(
    task: str,
    root: Path,
    client: AgentChatClient,
    max_rounds: int = 8,
) -> Iterator[dict[str, Any]]:
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
    yield {"type": "started", "max_rounds": max_rounds}
    plan_emitted = False

    try:
        for round_number in range(1, max_rounds + 1):
            message = _complete_with_empty_retry(client, messages, TOOL_DEFINITIONS)
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
                arguments, parse_error = _parse_arguments(call.arguments)
                display_arguments: Any = arguments if arguments is not None else call.arguments
                yield {
                    "type": "tool_call",
                    "round": round_number,
                    "call_id": call.id,
                    "tool": call.name,
                    "arguments": display_arguments,
                }

                result = parse_error or execute_tool(root, call.name, arguments or {})
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

        messages.append(
            {
                "role": "user",
                "content": (
                    "Tool round limit reached. Synthesize the available evidence now. "
                    "Do not request more tools and do not invent missing evidence."
                ),
            }
        )
        final_message = _complete_with_empty_retry(client, messages, None)
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
    except Exception:
        yield {
            "type": "error",
            "message": "Hy3 investigation failed. Check the API and retry.",
        }
        yield {"type": "done", "status": "error"}
