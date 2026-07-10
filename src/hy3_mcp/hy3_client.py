"""Thin client for the Hy3 API, using the OpenAI-compatible Chat Completions interface."""

from __future__ import annotations

from typing import Optional

from openai import OpenAI

from .config import Settings


class Hy3Client:
    """Minimal wrapper around the Hy3 OpenAI-compatible endpoint."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: Optional[OpenAI] = None

    def _ensure_client(self) -> OpenAI:
        if self._client is None:
            if not self.settings.api_key:
                raise RuntimeError(
                    "HY3_API_KEY is not set. Please export it as an environment "
                    "variable before calling Hy3-backed tools."
                )
            self._client = OpenAI(
                api_key=self.settings.api_key,
                base_url=self.settings.base_url,
            )
        return self._client

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Run a single chat completion and return the assistant message content."""
        client = self._ensure_client()
        resp = client.chat.completions.create(
            model=self.settings.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        content = resp.choices[0].message.content
        return content if content is not None else ""
