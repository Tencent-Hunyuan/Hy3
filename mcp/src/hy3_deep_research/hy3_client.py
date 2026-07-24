"""Thin wrapper around the OpenAI-compatible Tencent Hunyuan Hy3 API.

Centralises the recommended sampling parameters, the reasoning-effort
parameter format, timeout and retry logic — so the rest of the codebase
stays simple and testable.
"""

from __future__ import annotations

import time
from typing import Any

from openai import APITimeoutError, OpenAI, RateLimitError

from .config import Config

# Default timeout for a single Hy3 API call (seconds).
_DEFAULT_TIMEOUT = 120

# Retryable exception types.
_RETRYABLE = (APITimeoutError, RateLimitError, ConnectionError)


class Hy3Client:
    """Client for Tencent Hunyuan Hy3 via the OpenAI SDK."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._client = OpenAI(
            api_key=config.hunyuan_api_key,
            base_url=config.hunyuan_base_url,
            timeout=_DEFAULT_TIMEOUT,
            max_retries=2,
        )
        self._model = config.hunyuan_model

    def _build_extra_body(self, reasoning_effort: str) -> dict[str, Any]:
        """Build the extra_body for reasoning effort, honouring the configured format.

        - "template": extra_body={"chat_template_kwargs": {"reasoning_effort": <e>}}
          (used by self-deployed vLLM/SGLang servers and the official Hy3 recipe)
        - "top":      extra_body={"reasoning_effort": <e>}
          (some cloud setups accept the parameter at the top level)
        """
        if self._config.reasoning_format == "top":
            return {"reasoning_effort": reasoning_effort}
        return {"chat_template_kwargs": {"reasoning_effort": reasoning_effort}}

    def _create_with_retry(
        self, kwargs: dict[str, Any], max_retries: int = 3
    ) -> Any:
        """Call the Hy3 chat completion API with retry on transient errors.

        Retries on timeout, rate-limit and connection errors with exponential
        backoff (1s, 2s, 4s).  Any other exception is raised immediately.
        """
        last_exc: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                return self._client.chat.completions.create(**kwargs)
            except _RETRYABLE as exc:
                last_exc = exc
                if attempt < max_retries:
                    time.sleep(2 ** (attempt - 1))  # 1s, 2s, 4s
                continue
        # All retries exhausted — re-raise the last transient error.
        raise last_exc  # type: ignore[misc]

    def chat(
        self,
        messages: list[dict[str, Any]],
        reasoning_effort: str = "high",
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.9,
        top_p: float = 1.0,
    ) -> str:
        """Run a chat completion and return the assistant's text content."""
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "extra_body": self._build_extra_body(reasoning_effort),
        }
        if tools:
            kwargs["tools"] = tools

        response = self._create_with_retry(kwargs)
        content = response.choices[0].message.content
        return content if content is not None else ""

    def chat_full(
        self,
        messages: list[dict[str, Any]],
        reasoning_effort: str = "high",
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.9,
        top_p: float = 1.0,
    ):
        """Run a chat completion and return the raw response (for tool-call inspection)."""
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "extra_body": self._build_extra_body(reasoning_effort),
        }
        if tools:
            kwargs["tools"] = tools
        return self._create_with_retry(kwargs)
