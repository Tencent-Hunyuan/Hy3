from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI

from .config import Hy3Settings, ReasoningEffort


class Hy3Client:
    def __init__(self, settings: Hy3Settings) -> None:
        self.settings = settings
        self._client = AsyncOpenAI(
            base_url=settings.base_url,
            api_key=settings.api_key,
            timeout=settings.timeout_seconds,
        )

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        reasoning_effort: ReasoningEffort | None = None,
        temperature: float = 0.9,
        top_p: float = 1.0,
        max_tokens: int | None = None,
    ) -> str:
        params: dict[str, Any] = {
            "model": self.settings.model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
        }
        if self.settings.enable_reasoning_effort:
            effort = reasoning_effort or self.settings.default_reasoning_effort
            params["extra_body"] = {"chat_template_kwargs": {"reasoning_effort": effort}}
        if max_tokens is not None:
            params["max_tokens"] = max_tokens

        response = await self._client.chat.completions.create(**params)
        content = response.choices[0].message.content
        return content or ""

    async def health_check(self) -> dict[str, str]:
        message = await self.chat(
            [{"role": "user", "content": "Reply with exactly: ok"}],
            reasoning_effort="no_think",
            temperature=0.0,
            top_p=1.0,
            max_tokens=16,
        )
        return {
            "status": "ok" if "ok" in message.lower() else "unexpected_response",
            "base_url": self.settings.base_url,
            "model": self.settings.model,
            "response": message.strip(),
        }
