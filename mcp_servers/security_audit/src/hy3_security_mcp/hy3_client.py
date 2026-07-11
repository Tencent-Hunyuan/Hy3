"""Hy3 API client — a thin async wrapper around the OpenAI-compatible chat API."""

from __future__ import annotations

from typing import Literal, Protocol

import httpx
import openai
from openai.types.chat import ChatCompletionMessageParam

from hy3_security_mcp.config import Hy3Config

ReasoningEffort = Literal["no_think", "low", "high"]


class Hy3CompletionClient(Protocol):
    """The interface all Hy3-backed tools depend on. Tests fake this."""

    async def complete(
        self, system: str, user: str, *, reasoning_effort: ReasoningEffort = "no_think"
    ) -> str: ...


class Hy3ClientError(Exception):
    """Raised when the Hy3 API returns a response with no usable content."""


class Hy3Client:
    """Hy3CompletionClient implementation backed by openai.AsyncOpenAI."""

    def __init__(self, config: Hy3Config, *, http_client: httpx.AsyncClient | None = None) -> None:
        self._config = config
        self._client = openai.AsyncOpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=config.timeout_seconds,
            max_retries=2,
            http_client=http_client,
        )

    async def complete(
        self, system: str, user: str, *, reasoning_effort: ReasoningEffort = "no_think"
    ) -> str:
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        response = await self._client.chat.completions.create(
            model=self._config.model,
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
            messages=messages,
            extra_body={"chat_template_kwargs": {"reasoning_effort": reasoning_effort}},
        )
        choice = response.choices[0]
        content = choice.message.content
        if not content:
            raise Hy3ClientError(
                f"Hy3 model {self._config.model!r} returned empty content "
                f"(finish_reason={choice.finish_reason!r})"
            )
        return content
