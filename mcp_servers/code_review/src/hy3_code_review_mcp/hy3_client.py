from __future__ import annotations

from typing import Any, Dict

from .config import Hy3Settings


MAX_EMPTY_RESPONSE_RETRIES = 2
REQUEST_TIMEOUT_SECONDS = 30
EMPTY_RESPONSE_NUDGE = (
    "Your previous response was empty. Return a complete code review or test plan."
)


class Hy3Client:
    def __init__(self, settings: Hy3Settings, sdk_client: Any = None):
        self.settings = settings
        self.sdk_client = sdk_client

    @classmethod
    def from_env(cls) -> "Hy3Client":
        return cls(Hy3Settings.from_env())

    def _extra_body(self) -> Dict[str, Any]:
        effort = self.settings.reasoning_effort
        if not effort:
            return {}
        if "openrouter.ai" in self.settings.base_url:
            mapped = "none" if effort == "no_think" else effort
            return {"reasoning": {"effort": mapped}}
        return {"chat_template_kwargs": {"reasoning_effort": effort}}

    def complete(self, prompt: str) -> str:
        if self.sdk_client is None:
            from openai import OpenAI

            self.sdk_client = OpenAI(
                base_url=self.settings.base_url,
                api_key=self.settings.api_key,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a senior software engineer performing rigorous, "
                    "actionable code review. Prioritize correctness, security, "
                    "reliability, and missing tests."
                ),
            },
            {"role": "user", "content": prompt},
        ]
        for attempt in range(MAX_EMPTY_RESPONSE_RETRIES + 1):
            response = self.sdk_client.chat.completions.create(
                model=self.settings.model,
                messages=messages,
                temperature=self.settings.temperature,
                top_p=self.settings.top_p,
                max_tokens=self.settings.max_tokens,
                extra_body=self._extra_body(),
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            message = response.choices[0].message
            content = message.content or getattr(message, "reasoning", None)
            if content and content.strip():
                return content
            if attempt < MAX_EMPTY_RESPONSE_RETRIES:
                messages.append({"role": "user", "content": EMPTY_RESPONSE_NUDGE})

        raise RuntimeError("Hy3 returned an empty response after retries.")
