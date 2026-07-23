"""Thin client for the OpenAI-compatible Hy3 API."""

from __future__ import annotations

from typing import Protocol

from openai import APIError, APITimeoutError, AsyncOpenAI

from .config import Settings


class Analyzer(Protocol):
    async def complete(self, *, system_prompt: str, user_prompt: str) -> str: ...


class Hy3APIError(RuntimeError):
    """Raised when Hy3 cannot produce a response."""


class Hy3Client:
    def __init__(self, settings: Settings, client: AsyncOpenAI | None = None) -> None:
        self._settings = settings
        self._client = client or AsyncOpenAI(
            base_url=settings.base_url,
            api_key=settings.require_api_key(),
            timeout=settings.api_timeout_seconds,
        )

    async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        try:
            response = await self._client.chat.completions.create(
                model=self._settings.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self._settings.temperature,
                top_p=self._settings.top_p,
                max_tokens=self._settings.max_tokens,
                extra_body={
                    "chat_template_kwargs": {
                        "reasoning_effort": self._settings.reasoning_effort
                    }
                },
            )
        except APITimeoutError as exc:
            raise Hy3APIError("Hy3 API request timed out") from exc
        except APIError as exc:
            raise Hy3APIError(
                f"Hy3 API request failed ({getattr(exc, 'status_code', None) or 'unknown status'})"
            ) from exc
        except Exception as exc:
            raise Hy3APIError(f"Hy3 API request failed: {type(exc).__name__}") from exc

        content = response.choices[0].message.content if response.choices else None
        if not content or not content.strip():
            raise Hy3APIError("Hy3 API returned an empty response")
        return content.strip()
