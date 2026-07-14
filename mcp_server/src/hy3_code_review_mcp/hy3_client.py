"""Async client for an OpenAI-compatible Hy3 endpoint."""

from __future__ import annotations

from typing import Protocol

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

from .config import Settings


class Hy3ClientError(RuntimeError):
    """Raised when Hy3 cannot return a usable analysis."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "HY3_RESPONSE_ERROR",
        suggested_action: str = "Retry once and verify the configured Hy3 model and endpoint.",
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.suggested_action = suggested_action
        self.retryable = retryable


class Analyzer(Protocol):
    """Interface used by the review service and test doubles."""

    async def analyze(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        reasoning_effort: str | None = None,
    ) -> str: ...


class Hy3Client:
    """Call Hy3 through an OpenAI-compatible Chat Completions endpoint."""

    def __init__(self, settings: Settings, client: AsyncOpenAI | None = None) -> None:
        self.settings = settings
        self._client = client or AsyncOpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=settings.timeout,
        )

    async def analyze(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        reasoning_effort: str | None = None,
    ) -> str:
        """Request a grounded analysis and normalize API failures."""
        effort = reasoning_effort or self.settings.reasoning_effort
        try:
            response = await self._client.chat.completions.create(
                model=self.settings.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                top_p=1.0,
                extra_body={"chat_template_kwargs": {"reasoning_effort": effort}},
            )
        except APITimeoutError as exc:
            raise Hy3ClientError(
                "Hy3 request timed out",
                code="HY3_TIMEOUT",
                suggested_action="Retry once, reduce the diff size, or increase HY3_TIMEOUT.",
                retryable=True,
            ) from exc
        except APIConnectionError as exc:
            raise Hy3ClientError(
                "could not connect to the Hy3 endpoint",
                code="HY3_CONNECTION_ERROR",
                suggested_action="Check HY3_BASE_URL and network connectivity, then retry.",
                retryable=True,
            ) from exc
        except APIStatusError as exc:
            raise _status_error(exc) from exc

        if not response.choices:
            raise Hy3ClientError(
                "Hy3 returned no choices",
                suggested_action=(
                    "Retry once; if it persists, verify model compatibility with Chat Completions."
                ),
                retryable=True,
            )
        content = response.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise Hy3ClientError(
                "Hy3 returned an empty text response",
                suggested_action=(
                    "Retry once; if it persists, verify the model and response format."
                ),
                retryable=True,
            )
        return content.strip()


def _status_error(exc: APIStatusError) -> Hy3ClientError:
    status = exc.status_code
    if status in {401, 403}:
        return Hy3ClientError(
            f"Hy3 API returned HTTP {status}",
            code="HY3_AUTH_ERROR",
            suggested_action=(
                "Check HY3_API_KEY, model access, and whether the Key matches HY3_BASE_URL."
            ),
        )
    if status == 429:
        return Hy3ClientError(
            "Hy3 API returned HTTP 429",
            code="HY3_RATE_LIMITED",
            suggested_action=(
                "Wait for the service quota window or reduce request frequency, then retry."
            ),
            retryable=True,
        )
    if status >= 500:
        return Hy3ClientError(
            f"Hy3 API returned HTTP {status}",
            code="HY3_SERVICE_ERROR",
            suggested_action=(
                "Retry with backoff; check the provider status if the failure persists."
            ),
            retryable=True,
        )
    return Hy3ClientError(
        f"Hy3 API returned HTTP {status}",
        code="HY3_API_ERROR",
        suggested_action=(
            "Verify the model name and request compatibility with the configured endpoint."
        ),
    )
