# Copyright 2026 Tencent Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Thin async wrapper around the Hy3 OpenAI-compatible chat endpoint.

Real and offline mode share this exact code path (openai AsyncOpenAI SDK);
offline mode only swaps the HTTP transport for the deterministic fake in
:mod:`hy3_mcp.fake_backend`.  The API key is read from the environment here,
at construction time, and never stored on :class:`~hy3_mcp.settings.Settings`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import httpx
import openai
from mcp.server.fastmcp.exceptions import ToolError
from openai import AsyncOpenAI

from .fake_backend import build_fake_transport
from .settings import Settings

__all__ = ["Hy3Client", "Hy3Reply", "UsageCounter"]


@dataclass(frozen=True)
class Hy3Reply:
    """One completed Hy3 chat turn."""

    text: str
    prompt_tokens: int
    completion_tokens: int
    model: str


@dataclass
class UsageCounter:
    """Cumulative usage across the server lifetime (shown by ``hy3_status``)."""

    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "calls": self.calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
        }


@dataclass
class Hy3Client:
    """Async Hy3 chat client with usage accounting and clean tool errors."""

    settings: Settings
    http_client: httpx.AsyncClient | None = None
    usage: UsageCounter = field(default_factory=UsageCounter)

    def __post_init__(self) -> None:
        if self.settings.mode == "offline":
            http_client = self.http_client or httpx.AsyncClient(
                transport=build_fake_transport()
            )
            self._client = AsyncOpenAI(
                api_key="offline",  # sentinel; never used by the fake transport
                base_url="http://hy3.fake/v1",
                timeout=self.settings.timeout_seconds,  # same knob as real mode
                http_client=http_client,
            )
        else:
            # The real key is read HERE from the environment (never stored in
            # Settings). "EMPTY" matches the upstream README for self-hosted
            # vLLM / SGLang endpoints that do not check keys.
            self._client = AsyncOpenAI(
                api_key=os.environ.get("HY3_API_KEY") or "EMPTY",
                base_url=self.settings.api_base,
                timeout=self.settings.timeout_seconds,
                http_client=self.http_client,
            )

    async def chat(
        self,
        *,
        task: str,
        system: str,
        user: str,
        reasoning_effort: str | None = None,
    ) -> Hy3Reply:
        """Run one chat completion for tool ``task``.

        ``reasoning_effort`` is the per-tool default; a global
        ``HY3_REASONING_EFFORT`` env value overrides it.  It is forwarded to
        Hy3 through ``extra_body.chat_template_kwargs`` exactly as documented
        in the upstream README.
        """
        effort = self.settings.reasoning_effort or reasoning_effort or "no_think"
        system_full = f"[hy3-mcp task={task}]\n{system}"
        try:
            resp = await self._client.chat.completions.create(
                model=self.settings.model,
                messages=[
                    {"role": "system", "content": system_full},
                    {"role": "user", "content": user},
                ],
                temperature=self.settings.temperature,
                top_p=self.settings.top_p,
                max_tokens=self.settings.max_tokens,
                extra_body={"chat_template_kwargs": {"reasoning_effort": effort}},
            )
        except (openai.APIConnectionError, openai.APIStatusError) as exc:
            raise ToolError(
                f"Cannot reach the Hy3 backend (HY3_API_BASE={self.settings.api_base}): "
                f"{exc.__class__.__name__}: {exc}. "
                "Check that the endpoint is up and HY3_API_KEY is valid, or set "
                "HY3_MCP_OFFLINE=1 to use the built-in offline demo backend."
            ) from exc

        choice = resp.choices[0]
        text = choice.message.content or ""
        prompt_tokens = resp.usage.prompt_tokens if resp.usage else 0
        completion_tokens = resp.usage.completion_tokens if resp.usage else 0

        self.usage.calls += 1
        self.usage.prompt_tokens += prompt_tokens
        self.usage.completion_tokens += completion_tokens

        return Hy3Reply(
            text=text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=resp.model,
        )
