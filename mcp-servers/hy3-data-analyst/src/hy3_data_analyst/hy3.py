"""Hy3 OpenAI-compatible API client."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, TypedDict

from openai import AsyncOpenAI, OpenAIError

from .config import Settings

ReasoningEffort = Literal["no_think", "low", "medium", "high"]


class ChatMessage(TypedDict):
    role: Literal["system", "user"]
    content: str


class Hy3APIError(RuntimeError):
    """Raised when Hy3 cannot produce a response."""


async def call_hy3(
    messages: Sequence[ChatMessage],
    *,
    reasoning_effort: ReasoningEffort = "high",
    settings: Settings | None = None,
) -> str:
    """Call a Hy3 OpenAI-compatible chat-completions endpoint."""
    config = settings or Settings.from_env()
    client = AsyncOpenAI(
        base_url=config.api_base,
        api_key=config.api_key,
        timeout=config.timeout_seconds,
    )
    try:
        response = await client.chat.completions.create(
            model=config.model,
            messages=list(messages),
            temperature=0.6,
            top_p=0.95,
            extra_body={
                "chat_template_kwargs": {"reasoning_effort": reasoning_effort},
            },
        )
    except OpenAIError as exc:
        detail = _redact(str(exc), config.api_key)
        raise Hy3APIError(f"Hy3 API request failed ({type(exc).__name__}): {detail}") from exc
    finally:
        await client.close()

    content = response.choices[0].message.content if response.choices else None
    if not content:
        raise Hy3APIError("Hy3 API returned an empty response")
    return content


def _redact(message: str, api_key: str) -> str:
    if api_key and api_key != "EMPTY":
        return message.replace(api_key, "[REDACTED]")
    return message
