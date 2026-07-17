import os
from typing import Iterable

from openai import OpenAI


class Hy3Client:
    """Small OpenAI-compatible Hy3 client configured by environment variables."""

    def __init__(self) -> None:
        base_url = os.getenv("HY3_BASE_URL")
        if not base_url:
            raise RuntimeError("HY3_BASE_URL is required, for example http://127.0.0.1:8000/v1")

        api_key = os.getenv("HY3_API_KEY")
        if not api_key:
            raise RuntimeError("HY3_API_KEY is required. Use HY3_API_KEY=EMPTY for local deployments without auth.")

        self.model = os.getenv("HY3_MODEL", "hy3")
        self.reasoning_effort = os.getenv("HY3_REASONING_EFFORT", "no_think")
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        kwargs: dict = dict(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=float(os.getenv("HY3_TEMPERATURE", "0.9")),
            top_p=float(os.getenv("HY3_TOP_P", "1.0")),
        )
        # Hy3 (vLLM/SGLang) understands chat_template_kwargs.reasoning_effort.
        # Other OpenAI-compatible endpoints (DeepSeek, Qwen, ...) may reject it,
        # so this is opt-in and disabled by default for non-Hy3 backends.
        if os.getenv("HY3_SEND_REASONING_EFFORT", "true").lower() in ("1", "true", "yes", "on"):
            kwargs["extra_body"] = {
                "chat_template_kwargs": {
                    "reasoning_effort": self.reasoning_effort,
                }
            }
        response = self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        return content or ""


def truncate_text(text: str, max_chars: int = 24000) -> str:
    if len(text) <= max_chars:
        return text
    omitted = len(text) - max_chars
    return text[:max_chars] + f"\n\n[Truncated {omitted} characters before sending to Hy3.]"


def format_paragraphs(paragraphs: Iterable[str]) -> str:
    return "\n".join(p.strip() for p in paragraphs if p and p.strip())