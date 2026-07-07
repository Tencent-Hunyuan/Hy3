from __future__ import annotations

from typing import Any, Dict

from .config import Hy3Settings


class Hy3Client:
    def __init__(self, settings: Hy3Settings):
        self.settings = settings

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
        from openai import OpenAI

        client = OpenAI(base_url=self.settings.base_url, api_key=self.settings.api_key)
        response = client.chat.completions.create(
            model=self.settings.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior software engineer performing rigorous, "
                        "actionable code review. Prioritize correctness, security, "
                        "reliability, and missing tests."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=self.settings.temperature,
            top_p=self.settings.top_p,
            max_tokens=self.settings.max_tokens,
            extra_body=self._extra_body(),
        )
        message = response.choices[0].message
        content = message.content or getattr(message, "reasoning", None)
        return content or ""
