"""Small asynchronous wrapper around the OpenAI-compatible Hy3 endpoint."""

from __future__ import annotations

from dataclasses import dataclass

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

from .errors import ProviderError
from .models import Usage
from .settings import Settings


@dataclass(frozen=True, slots=True)
class ModelReply:
    content: str
    usage: Usage


class Hy3Client:
    """Call Hy3 while keeping credentials and provider details out of tool results."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncOpenAI(
            api_key=settings.require_api_key(),
            base_url=settings.base_url,
            timeout=settings.timeout_seconds,
            max_retries=settings.max_retries,
        )

    async def complete(self, *, system: str, user: str) -> ModelReply:
        try:
            response = await self._client.chat.completions.create(
                model=self._settings.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
                top_p=1.0,
                max_tokens=self._settings.max_output_tokens,
                extra_body={
                    "chat_template_kwargs": {
                        "reasoning_effort": self._settings.reasoning_effort,
                    }
                },
            )
        except APITimeoutError as exc:
            raise ProviderError(
                "Hy3 request timed out; retry with a smaller specification"
            ) from exc
        except APIConnectionError as exc:
            raise ProviderError("Could not connect to the configured Hy3 endpoint") from exc
        except APIStatusError as exc:
            if exc.status_code in {401, 403}:
                message = "Hy3 rejected the API key or model access"
            elif exc.status_code == 429:
                message = "Hy3 rate limit exceeded; retry later"
            else:
                message = f"Hy3 returned provider error HTTP {exc.status_code}"
            raise ProviderError(message) from exc

        content = response.choices[0].message.content if response.choices else None
        if not content or not content.strip():
            raise ProviderError("Hy3 returned an empty response")
        provider_usage = response.usage
        usage = Usage(
            prompt_tokens=getattr(provider_usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(provider_usage, "completion_tokens", 0) or 0,
            total_tokens=getattr(provider_usage, "total_tokens", 0) or 0,
        )
        return ModelReply(content=content.strip(), usage=usage)
