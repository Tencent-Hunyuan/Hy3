"""Async Hy3 client.

Hy3 is served through an OpenAI-compatible ``/chat/completions`` endpoint
(see the repository README). This client centralises:

* authentication header construction,
* request body construction,
* timeout handling,
* limited retry with exponential back-off for 429 / 5xx,
* non-success status-code mapping to typed exceptions,
* JSON extraction + Pydantic structured-output validation with one repair retry,
* sensitive-data masking,
* graceful client shutdown.

The API key is never written to logs or exception messages.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from .config import Settings
from .exceptions import (
    Hy3APIError,
    Hy3AuthenticationError,
    Hy3RateLimitError,
    Hy3TimeoutError,
    ModelOutputError,
)

logger = logging.getLogger("hy3_architecture_mcp.client")


def _redact_url(url: str) -> str:
    """Strip any query string from a URL before logging."""
    if "?" in url:
        return url.split("?", 1)[0]
    return url


# Matches a JSON object/array possibly wrapped in ```json ... ``` fences.
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _extract_json(text: str) -> Any:
    """Best-effort extraction of a JSON value from model output text.

    Handles ```json fenced blocks, bare JSON, and leading prose.
    Raises ``json.JSONDecodeError`` if no JSON could be parsed.
    """
    if not text or not text.strip():
        raise json.JSONDecodeError("empty content", text or "", 0)

    fenced = _JSON_FENCE_RE.search(text)
    candidates: list[str] = []
    if fenced:
        candidates.append(fenced.group(1))
    # Then try the whole text and a brace/bracket scan as fallbacks.
    candidates.append(text)

    # Locate first '{' ... '}' or '[' ... ']' slice.
    for start_ch, end_ch in (("{", "}"), ("[", "]")):
        s = text.find(start_ch)
        e = text.rfind(end_ch)
        if s != -1 and e != -1 and e > s:
            candidates.append(text[s : e + 1])

    last_err: Exception | None = None
    for cand in candidates:
        try:
            return json.loads(cand.strip().removeprefix("```json").removesuffix("```").strip())
        except json.JSONDecodeError as err:
            last_err = err
            continue
    assert last_err is not None
    raise last_err


class Hy3Client:
    """Async OpenAI-compatible client with structured-output validation."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.base_url,
            timeout=httpx.Timeout(settings.timeout_seconds),
            headers={
                "Authorization": f"Bearer {settings.api_key.get_secret_value()}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

    # -- lifecycle ---------------------------------------------------------

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> Hy3Client:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    # -- low-level HTTP ----------------------------------------------------

    def _build_body(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        return {
            "model": self._settings.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "top_p": 1.0,
            # vLLM / SGLang accept chat_template_kwargs at the top level to
            # switch reasoning effort. Falls back gracefully if ignored.
            "chat_template_kwargs": {"reasoning_effort": self._settings.reasoning_effort},
        }

    async def _chat(self, *, system_prompt: str, user_prompt: str) -> str:
        url = "/chat/completions"
        body = self._build_body(system_prompt=system_prompt, user_prompt=user_prompt)
        last_exc: Exception | None = None

        for attempt in range(self._settings.max_retries + 1):
            try:
                resp = await self._client.post(url, json=body)
            except httpx.TimeoutException as exc:
                raise Hy3TimeoutError(
                    f"Hy3 request timed out after {self._settings.timeout_seconds:g}s. "
                    "Increase HY3_TIMEOUT_SECONDS or check the deployment load."
                ) from exc
            except httpx.HTTPError as exc:
                last_exc = exc
                logger.warning(
                    "Transient transport error contacting Hy3 (attempt %d/%d): %s",
                    attempt + 1,
                    self._settings.max_retries + 1,
                    _redact_url(str(exc)),
                )
                await self._backoff(attempt)
                continue

            if resp.status_code == 429 or 500 <= resp.status_code < 600:
                last_exc = self._status_error(resp)
                logger.warning(
                    "Hy3 returned HTTP %d (attempt %d/%d); backing off",
                    resp.status_code,
                    attempt + 1,
                    self._settings.max_retries + 1,
                )
                if attempt < self._settings.max_retries:
                    await self._backoff(attempt)
                    continue
                raise self._status_error(resp)

            if resp.status_code in (401, 403):
                raise Hy3AuthenticationError(
                    f"Hy3 rejected the API key (HTTP {resp.status_code}). "
                    "Verify HY3_API_KEY matches the deployment."
                )
            if resp.status_code >= 400:
                raise self._status_error(resp)

            try:
                payload = resp.json()
            except json.JSONDecodeError as exc:
                raise Hy3APIError(
                    "Hy3 returned a non-JSON response. Confirm HY3_BASE_URL points "
                    "to an OpenAI-compatible /v1 endpoint."
                ) from exc

            try:
                return payload["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as exc:
                snippet = str(payload)[:160]
                logger.warning("Unexpected Hy3 response shape: %s", snippet)
                raise Hy3APIError(
                    "Hy3 response did not contain choices[0].message.content."
                ) from exc

        # Exhausted retries on transport errors.
        assert last_exc is not None
        raise Hy3APIError(
            f"Hy3 request failed after {self._settings.max_retries + 1} attempts: "
            f"{_redact_url(type(last_exc).__name__)}"
        ) from last_exc

    async def _backoff(self, attempt: int) -> None:
        # Exponential back-off: 0.5s, 1s, 2s, ... capped at 8s with jitter-free base.
        delay = min(8.0, 0.5 * (2**attempt))
        await asyncio.sleep(delay)

    def _status_error(self, resp: httpx.Response) -> Exception:
        status = resp.status_code
        if status == 429:
            return Hy3RateLimitError(
                "Hy3 rate-limited the request after retries. Reduce call rate "
                "or raise HY3_MAX_RETRIES."
            )
        # Do not echo the raw body which may contain sensitive context.
        return Hy3APIError(f"Hy3 returned HTTP {status}. Check HY3_BASE_URL and HY3_MODEL.")

    # -- structured output -------------------------------------------------

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
    ) -> BaseModel:
        """Call Hy3 and validate the response into ``response_model``.

        On the first parse failure a single repair request is sent that shows
        the validation errors and asks the model to emit valid JSON. If the
        second attempt also fails, ``ModelOutputError`` is raised. The raw
        model output is never written to logs.
        """
        content = await self._chat(system_prompt=system_prompt, user_prompt=user_prompt)
        first_error: Exception | None = None
        try:
            parsed = _extract_json(content)
            return response_model.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as err:
            # ``err`` is unbound after the except clause; capture it explicitly.
            first_error = err
            logger.warning(
                "Hy3 output failed schema validation (%s); sending one repair request",
                type(err).__name__,
            )

        assert first_error is not None
        repair_system = (
            "You are a JSON repair assistant. Return ONLY a single valid JSON "
            "object that satisfies the requested schema. Do not include any "
            "prose, markdown, or code fences."
        )
        repair_user = (
            f"The previous output could not be parsed because:\n{first_error}\n\n"
            f"Re-emit ONLY a valid JSON object for this schema:\n"
            f"{json.dumps(response_model.model_json_schema(), ensure_ascii=False)}"
        )
        content2 = await self._chat(system_prompt=repair_system, user_prompt=repair_user)
        try:
            parsed2 = _extract_json(content2)
            return response_model.model_validate(parsed2)
        except (json.JSONDecodeError, ValidationError) as second_err:
            raise ModelOutputError(
                "Hy3 output could not be parsed into the expected schema even "
                "after a repair attempt. Retry with a clearer requirement or a "
                "different model."
            ) from second_err
