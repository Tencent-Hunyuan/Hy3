from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from .config import Settings


@dataclass(frozen=True)
class Hy3Result:
    content: str
    mode: str
    model: str


class Hy3Client:
    def __init__(self, settings: Settings):
        self.settings = settings

    def complete(self, system: str, user: str, *, reasoning_effort: str | None = None) -> Hy3Result:
        if self.settings.offline:
            return Hy3Result(
                content=self._offline_answer(system, user),
                mode="offline",
                model=self.settings.model,
            )

        payload = {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.9,
            "top_p": 1.0,
            "chat_template_kwargs": {
                "reasoning_effort": reasoning_effort or self.settings.reasoning_effort,
            },
        }
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.settings.api_base}/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.settings.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"Hy3 API returned HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Hy3 API request failed: {exc.reason}") from exc

        content = body.get("choices", [{}])[0].get("message", {}).get("content")
        if not isinstance(content, str):
            raise RuntimeError("Hy3 API response did not contain choices[0].message.content")
        return Hy3Result(content=content, mode="real", model=self.settings.model)

    @staticmethod
    def _offline_answer(system: str, user: str) -> str:
        topic = "lead intelligence"
        lowered = f"{system}\n{user}".lower()
        if "outreach" in lowered or "外联" in lowered:
            topic = "outreach plan"
        elif "knowledge" in lowered or "citation" in lowered or "证据" in lowered:
            topic = "grounded knowledge answer"
        elif "batch" in lowered or "csv" in lowered:
            topic = "batch scoring report"
        return (
            f"[OFFLINE HY3 MOCK] Drafted a {topic}. "
            "Set HY3_API_KEY and HY3_API_BASE to call a real Hy3 OpenAI-compatible endpoint."
        )
