from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any, Literal

import httpx

from hy3_ci_copilot.config import Settings
from hy3_ci_copilot.errors import Hy3APIError
from hy3_ci_copilot.security import sanitize_untrusted_text

ReasoningEffort = Literal["no_think", "low", "high"]
DEFAULT_MAX_RESPONSE_BYTES = 8 * 1024 * 1024


class Hy3Client:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    ) -> None:
        self.settings = settings
        self.transport = transport
        self.max_response_bytes = max_response_bytes

    def _request_body(
        self,
        system_prompt: str,
        user_prompt: str,
        reasoning_effort: ReasoningEffort,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.9,
            "top_p": 1.0,
            "max_tokens": self.settings.max_output_tokens,
        }
        if self.settings.resolved_api_style == "openrouter":
            effort = "none" if reasoning_effort == "no_think" else reasoning_effort
            body["reasoning"] = {"effort": effort}
        else:
            body["chat_template_kwargs"] = {"reasoning_effort": reasoning_effort}
        return body

    def _redact_api_key(self, text: str) -> str:
        api_key = self.settings.api_key
        if not api_key or api_key == "EMPTY":
            return text
        return text.replace(api_key, "[REDACTED]")

    async def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        reasoning_effort: ReasoningEffort,
    ) -> str:
        try:
            return await asyncio.wait_for(
                self._complete_with_retries(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    reasoning_effort=reasoning_effort,
                ),
                timeout=self.settings.timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise Hy3APIError(
                f"Hy3 request timed out after {self.settings.timeout_seconds:g} seconds."
            ) from exc

    async def _complete_with_retries(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        reasoning_effort: ReasoningEffort,
    ) -> str:
        url = f"{self.settings.base_url}/chat/completions"
        headers = {
            "Accept-Encoding": "identity",
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
            "X-Title": "Hy3 CI Copilot",
        }
        timeout = httpx.Timeout(self.settings.timeout_seconds)
        async with httpx.AsyncClient(
            timeout=timeout,
            transport=self.transport,
            follow_redirects=False,
        ) as client:
            for attempt in range(self.settings.max_retries + 1):
                try:
                    should_retry = False
                    async with client.stream(
                        "POST",
                        url,
                        headers=headers,
                        json=self._request_body(system_prompt, user_prompt, reasoning_effort),
                    ) as streamed_response:
                        if (
                            streamed_response.status_code in {429, 500, 502, 503, 504}
                            and attempt < self.settings.max_retries
                        ):
                            should_retry = True
                        else:
                            content = await self._read_limited_response(streamed_response)
                            # aiter_bytes() returns decoded bytes; representation headers are stale.
                            buffered_headers = [
                                (name, value)
                                for name, value in streamed_response.headers.multi_items()
                                if name.lower() not in {"content-encoding", "content-length"}
                            ]
                            response = httpx.Response(
                                status_code=streamed_response.status_code,
                                headers=buffered_headers,
                                content=content,
                                request=streamed_response.request,
                            )
                except httpx.TimeoutException as exc:
                    if attempt < self.settings.max_retries:
                        await asyncio.sleep(0.5 * (2**attempt))
                        continue
                    raise Hy3APIError(
                        f"Hy3 request timed out after {self.settings.timeout_seconds:g} seconds."
                    ) from exc
                except httpx.HTTPError:
                    raise Hy3APIError(
                        "Could not reach the Hy3 endpoint. Check HY3_BASE_URL and network "
                        "connectivity."
                    ) from None

                if should_retry:
                    await asyncio.sleep(0.5 * (2**attempt))
                    continue
                if response.is_error:
                    detail = sanitize_untrusted_text(
                        self._redact_api_key(response.text)[:500]
                    )
                    if response.status_code in {401, 403}:
                        raise Hy3APIError(
                            "Hy3 authentication failed "
                            f"({response.status_code}). Check HY3_API_KEY."
                        )
                    raise Hy3APIError(
                        f"Hy3 endpoint returned HTTP {response.status_code}: "
                        f"{detail or 'no details'}"
                    )
                return sanitize_untrusted_text(
                    self._redact_api_key(self._extract_content(response))
                )

        raise Hy3APIError("Hy3 request failed without a response.")

    async def _read_limited_response(self, response: httpx.Response) -> bytes:
        content = bytearray()
        async for chunk in response.aiter_bytes(chunk_size=64 * 1024):
            if len(content) + len(chunk) > self.max_response_bytes:
                raise Hy3APIError(
                    f"Hy3 response exceeded the {self.max_response_bytes}-byte safety limit."
                )
            content.extend(chunk)
        return bytes(content)

    @staticmethod
    def _extract_content(response: httpx.Response) -> str:
        try:
            payload = response.json()
            message = payload["choices"][0]["message"]
            content = message["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise Hy3APIError("Hy3 returned an invalid Chat Completions response.") from exc

        if isinstance(content, str) and content.strip():
            return content.strip()
        if isinstance(content, list):
            parts = [
                str(item.get("text", ""))
                for item in content
                if isinstance(item, Mapping) and item.get("type") in {None, "text"}
            ]
            joined = "".join(parts).strip()
            if joined:
                return joined
        raise Hy3APIError("Hy3 returned an empty response.")
