"""Small OpenAI-compatible client for Hy3 chat completions."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Iterable
from urllib import error, request


@dataclass(frozen=True)
class Hy3Settings:
    base_url: str
    api_key: str
    model: str = "hy3"
    timeout_seconds: int = 60
    mock: bool = False

    @classmethod
    def from_env(cls) -> "Hy3Settings":
        return cls(
            base_url=os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1").rstrip("/"),
            api_key=os.getenv("HY3_API_KEY", ""),
            model=os.getenv("HY3_MODEL", "hy3"),
            timeout_seconds=int(os.getenv("HY3_TIMEOUT_SECONDS", "60")),
            mock=os.getenv("HY3_MOCK", "").lower() in {"1", "true", "yes", "on"},
        )


class Hy3Client:
    """Calls Hy3 through the OpenAI-compatible chat completions endpoint."""

    def __init__(self, settings: Hy3Settings | None = None) -> None:
        self.settings = settings or Hy3Settings.from_env()

    def chat(self, system: str, user: str, *, reasoning_effort: str = "high") -> str:
        if self.settings.mock:
            return self._mock_response(system, user)

        if not self.settings.api_key:
            raise RuntimeError("HY3_API_KEY is required unless HY3_MOCK=1 is set.")

        payload = {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "top_p": 1.0,
            "extra_body": {
                "chat_template_kwargs": {
                    "reasoning_effort": reasoning_effort,
                }
            },
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.settings.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.settings.timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Hy3 API returned HTTP {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Hy3 API request failed: {exc.reason}") from exc

        return data["choices"][0]["message"]["content"]

    @staticmethod
    def _mock_response(system: str, user: str) -> str:
        preview = compact_lines(user.splitlines(), limit=8)
        return (
            "Mock Hy3 response\n\n"
            "Summary: the request was parsed successfully and would be sent to Hy3 in live mode.\n\n"
            "Key evidence:\n"
            f"{preview}\n\n"
            "Recommended next step: run again with HY3_BASE_URL, HY3_API_KEY, and HY3_MODEL configured."
        )


def compact_lines(lines: Iterable[str], *, limit: int) -> str:
    kept = []
    for raw in lines:
        line = raw.strip()
        if line:
            kept.append(line[:180])
        if len(kept) >= limit:
            break
    return "\n".join(f"- {line}" for line in kept) or "- No input content supplied."
