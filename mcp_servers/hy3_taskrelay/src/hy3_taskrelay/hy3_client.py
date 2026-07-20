"""Bounded OpenAI-compatible HTTP client for the Hy3 API."""

from __future__ import annotations

import asyncio
import json
import math
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from hy3_taskrelay.config import Settings
from hy3_taskrelay.errors import Hy3APIError

RETRYABLE_STATUS_CODES = {429, 502, 503, 504}
DEFAULT_TIMEOUT_SECONDS = 45.0
MAX_RESPONSE_CHARACTERS = 100_000
MAX_RESPONSE_BYTES = 512_000
TEMPERATURE = 0.9
TOP_P = 1.0
REASONING_EFFORT = "high"


class Hy3Client:
    """Call Hy3 with strict timeouts, finite retries, and safe errors."""

    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = 2,
    ) -> None:
        self._settings = settings
        self._transport = transport
        self._sleep = sleep
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries

    async def complete(self, messages: list[dict[str, str]]) -> str:
        """Return Hy3 assistant text without exposing response metadata or request IDs."""

        endpoint = f"{self._settings.base_url.rstrip('/')}/chat/completions"
        payload: dict[str, Any] = {
            "model": self._settings.model,
            "messages": messages,
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "chat_template_kwargs": {"reasoning_effort": REASONING_EFFORT},
        }
        headers = {
            "Authorization": f"Bearer {self._settings.api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }
        timeout = httpx.Timeout(self._timeout_seconds)
        async with httpx.AsyncClient(
            transport=self._transport,
            timeout=timeout,
            follow_redirects=False,
        ) as client:
            for attempt in range(self._max_retries + 1):
                retry_delay: float | None = None
                try:
                    async with client.stream(
                        "POST", endpoint, headers=headers, json=payload
                    ) as response:
                        if response.status_code in RETRYABLE_STATUS_CODES:
                            if attempt >= self._max_retries:
                                raise Hy3APIError(
                                    "Hy3 is temporarily unavailable after "
                                    f"{attempt + 1} attempts (HTTP {response.status_code}). "
                                    "Try again later."
                                )
                            retry_delay = self._retry_delay(response, attempt)
                        elif response.status_code in {401, 403}:
                            raise Hy3APIError(
                                f"Hy3 authentication failed (HTTP {response.status_code}). Check "
                                "HY3_API_KEY and its permissions."
                            )
                        elif response.status_code == 400:
                            raise Hy3APIError(
                                "Hy3 rejected the request (HTTP 400). Check HY3_MODEL and the "
                                "documented input limits."
                            )
                        elif not 200 <= response.status_code < 300:
                            raise Hy3APIError(
                                f"Hy3 request failed (HTTP {response.status_code}). Check "
                                "HY3_BASE_URL and HY3_MODEL."
                            )
                        else:
                            return await self._assistant_text(response)
                except (httpx.TransportError, httpx.InvalidURL):
                    if attempt >= self._max_retries:
                        raise Hy3APIError(
                            "Hy3 could not be reached after limited retries. Check "
                            "HY3_BASE_URL and network connectivity."
                        ) from None
                    await self._sleep(0.5 * (2**attempt))
                    continue
                assert retry_delay is not None
                await self._sleep(retry_delay)

        raise AssertionError("unreachable")

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After", "").strip()
        if retry_after:
            try:
                parsed = float(retry_after)
            except ValueError:
                try:
                    retry_date = parsedate_to_datetime(retry_after)
                    if retry_date.tzinfo is None:
                        retry_date = retry_date.replace(tzinfo=timezone.utc)
                    parsed = (retry_date - datetime.now(timezone.utc)).total_seconds()
                    return min(max(parsed, 0.0), 30.0)
                except (TypeError, ValueError, OverflowError):
                    parsed = math.nan
            if math.isfinite(parsed) and parsed >= 0:
                return min(parsed, 30.0)
        return 0.5 * (2**attempt)

    @staticmethod
    async def _assistant_text(response: httpx.Response) -> str:
        content_length = response.headers.get("Content-Length", "")
        if content_length.isdigit() and int(content_length) > MAX_RESPONSE_BYTES:
            raise Hy3APIError(
                f"Hy3 response exceeds the {MAX_RESPONSE_BYTES}-byte transport safety limit."
            )
        body = bytearray()
        async for chunk in response.aiter_bytes():
            body.extend(chunk)
            if len(body) > MAX_RESPONSE_BYTES:
                raise Hy3APIError(
                    f"Hy3 response exceeds the {MAX_RESPONSE_BYTES}-byte transport safety limit."
                )
        try:
            data = json.loads(body.decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
        except (UnicodeDecodeError, ValueError, KeyError, IndexError, TypeError):
            raise Hy3APIError(
                "Hy3 returned an invalid response envelope. Retry the call or verify HY3_BASE_URL."
            ) from None
        if not isinstance(content, str) or not content.strip():
            raise Hy3APIError("Hy3 returned an empty assistant response. Retry the call.")
        if len(content) > MAX_RESPONSE_CHARACTERS:
            raise Hy3APIError(
                f"Hy3 response exceeds the {MAX_RESPONSE_CHARACTERS}-character safety limit."
            )
        return content
