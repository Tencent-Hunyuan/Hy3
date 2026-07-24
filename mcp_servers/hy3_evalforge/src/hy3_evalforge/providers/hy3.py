"""OpenAI-compatible Hy3 provider with bounded retry behavior."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

from hy3_evalforge.errors import ErrorCode, EvalForgeError
from hy3_evalforge.providers.base import ProviderRequest, ProviderResponse
from hy3_evalforge.settings import Settings

Sleep = Callable[[float], Awaitable[None]]


class Hy3Provider:
    """Call Hy3 without exposing credentials, prompts, or raw errors to callers."""

    def __init__(
        self,
        settings: Settings,
        *,
        client: Any | None = None,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._settings = settings
        self._client = client or AsyncOpenAI(
            base_url=settings.hy3_base_url,
            api_key=settings.require_hy3_api_key(),
            timeout=settings.request_timeout_seconds,
            max_retries=0,
        )
        self._sleep = sleep

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        """Make one bounded request, retrying only transient provider failures."""
        for attempt in range(self._settings.retry_attempts + 1):
            try:
                response = await self._client.chat.completions.create(
                    model=self._settings.hy3_model,
                    messages=[
                        {"role": "system", "content": request.system_prompt},
                        {"role": "user", "content": request.user_prompt},
                    ],
                    temperature=0.9,
                    top_p=1.0,
                    response_format={"type": "json_object"},
                    extra_body={
                        "chat_template_kwargs": {"reasoning_effort": request.reasoning_effort}
                    },
                )
                content = response.choices[0].message.content
                if not isinstance(content, str) or not content.strip():
                    raise EvalForgeError(
                        ErrorCode.HY3_OUTPUT_INVALID,
                        "Hy3 returned an empty response.",
                    )
                return ProviderResponse(content=content)
            except EvalForgeError:
                raise
            except (APIConnectionError, APITimeoutError, APIStatusError) as exc:
                if attempt >= self._settings.retry_attempts or not _is_retryable(exc):
                    raise EvalForgeError(
                        ErrorCode.PROVIDER_ERROR,
                        "Hy3 request failed; verify provider availability and retry later.",
                    ) from exc
                await self._sleep(2**attempt)
            except Exception as exc:
                raise EvalForgeError(
                    ErrorCode.PROVIDER_ERROR,
                    "Hy3 request failed; verify provider configuration.",
                ) from exc


def _is_retryable(error: APIConnectionError | APITimeoutError | APIStatusError) -> bool:
    """Only retry network failures, timeouts, 429s, and server-side errors."""
    if isinstance(error, (APIConnectionError, APITimeoutError)):
        return True
    return error.status_code == 429 or error.status_code >= 500
