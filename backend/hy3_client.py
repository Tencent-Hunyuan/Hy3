"""
Hy3 API client - OpenAI-compatible wrapper for the Hy3 model.

Hy3 is served through an OpenAI-compatible endpoint. We use the official
OpenAI SDK with a custom base_url and an extra_body field for reasoning_effort.
"""
import logging
from typing import List, Dict, Iterator, Optional

from openai import OpenAI

import config

logger = logging.getLogger(__name__)

# Recommended generation parameters for Hy3
DEFAULT_TEMPERATURE = 0.9
DEFAULT_TOP_P = 1.0


class Hy3Client:
    """Thin wrapper around the OpenAI SDK pointed at the Hy3 endpoint."""

    def __init__(
        self,
        api_base: str = None,
        api_key: str = None,
        model: str = None,
        timeout: int = None,
    ):
        self.api_base = api_base or config.HY3_API_BASE
        self.api_key = api_key or config.HY3_API_KEY
        self.model = model or config.HY3_MODEL
        self.timeout = timeout or config.HY3_TIMEOUT
        if not self.api_key:
            logger.warning("HY3_API_KEY is not set - API calls will fail.")
        self.client = OpenAI(
            base_url=self.api_base,
            api_key=self.api_key,
            timeout=self.timeout,
        )

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = DEFAULT_TEMPERATURE,
        top_p: float = DEFAULT_TOP_P,
        reasoning_effort: str = "low",
        max_tokens: Optional[int] = None,
    ) -> str:
        """Non-streaming completion. Returns the full answer text."""
        kwargs = dict(
            model=self.model,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            extra_body={"reasoning_effort": reasoning_effort},
        )
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        resp = self.client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = DEFAULT_TEMPERATURE,
        top_p: float = DEFAULT_TOP_P,
        reasoning_effort: str = "low",
        max_tokens: Optional[int] = None,
    ) -> Iterator[str]:
        """Streaming completion. Yields text deltas as they arrive."""
        kwargs = dict(
            model=self.model,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            stream=True,
            extra_body={"reasoning_effort": reasoning_effort},
        )
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        stream = self.client.chat.completions.create(**kwargs)
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content


# Module-level singleton
_client: Optional[Hy3Client] = None


def get_client() -> Hy3Client:
    global _client
    if _client is None:
        _client = Hy3Client()
    return _client
