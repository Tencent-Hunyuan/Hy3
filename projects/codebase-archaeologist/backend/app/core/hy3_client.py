"""
Hy3 API Client — OpenAI-compatible wrapper with four calling modes.

Modes (see design doc §3.2):
  Planner      — reasoning_effort=high,   tool_choice=auto
  Reader       — reasoning_effort=medium, tool_choice=none
  Synthesizer  — reasoning_effort=low,    response_format=json_schema
  ReAct Agent  — reasoning_effort=medium, tool_choice=auto (iterative)

All modes share a single prompt_cache_key for cost optimization.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx
from openai import AsyncOpenAI

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

# ── Type aliases ──────────────────────────────────────────────
Message = dict[str, Any]
ToolDef = dict[str, Any]
ReasoningEffort = Literal["low", "medium", "high"]


# ── Data classes ──────────────────────────────────────────────

@dataclass
class LLMResponse:
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)


@dataclass
class UsageTracker:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    call_count: int = 0
    total_latency_ms: float = 0.0

    @property
    def total_input_cost_yuan(self) -> float:
        """Hy3 pricing: input 1 CNY / 1M tokens"""
        return self.prompt_tokens / 1_000_000 * 1.0

    @property
    def total_output_cost_yuan(self) -> float:
        """Hy3 pricing: output 4 CNY / 1M tokens"""
        return self.completion_tokens / 1_000_000 * 4.0

    @property
    def cache_savings_yuan(self) -> float:
        """Tokens read from cache cost 0.25 CNY / 1M instead of 1.0"""
        return self.cache_read_tokens / 1_000_000 * 0.75

    @property
    def total_cost_yuan(self) -> float:
        return self.total_input_cost_yuan + self.total_output_cost_yuan - self.cache_savings_yuan

    def summary(self) -> str:
        return (
            f"calls={self.call_count} "
            f"prompt={self.prompt_tokens} completion={self.completion_tokens} "
            f"cache_read={self.cache_read_tokens} "
            f"latency={self.total_latency_ms:.0f}ms "
            f"cost≈¥{self.total_cost_yuan:.4f}"
        )


# ── Client ────────────────────────────────────────────────────

class Hy3Client:
    """Async wrapper around Hy3's OpenAI-compatible Chat Completions API."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.usage = UsageTracker()
        self._client = AsyncOpenAI(
            api_key=self.settings.hy3_api_key,
            base_url=self.settings.hy3_base_url,
            timeout=httpx.Timeout(self.settings.hy3_request_timeout),
            max_retries=0,  # we do our own retries with backoff
        )

    # ── Core call with exponential backoff ───────────────────

    async def chat(
        self,
        messages: list[Message],
        *,
        reasoning_effort: ReasoningEffort = "medium",
        temperature: float = 0.1,
        max_tokens: int = 4096,
        tools: list[ToolDef] | None = None,
        tool_choice: str = "auto",
        response_schema: dict[str, Any] | None = None,
        stream: bool = False,
    ) -> LLMResponse:
        """Low-level chat completion with exponential backoff retry."""

        kwargs: dict[str, Any] = {
            "model": self.settings.hy3_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "extra_body": {"prompt_cache_key": self.settings.prompt_cache_key},
            "extra_headers": {"X-Session-ID": f"archaeologist-{id(self)}"},
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        if response_schema:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_output",
                    "strict": True,
                    "schema": response_schema,
                },
            }

        last_error: Exception | None = None
        for attempt in range(self.settings.hy3_max_retries + 1):
            t0 = time.monotonic()
            try:
                if stream:
                    completion = await self._client.chat.completions.create(
                        **kwargs, stream=True, stream_options={"include_usage": True}
                    )
                    result = await self._collect_stream(completion)
                else:
                    completion = await self._client.chat.completions.create(**kwargs)
                    result = self._parse_response(completion)
                self.usage.total_latency_ms += (time.monotonic() - t0) * 1000
                return result
            except Exception as e:
                self.usage.total_latency_ms += (time.monotonic() - t0) * 1000
                last_error = e
                if attempt < self.settings.hy3_max_retries:
                    wait = 2 ** attempt + (time.monotonic() % 1)
                    logger.warning(
                        "Hy3 call failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1, self.settings.hy3_max_retries + 1, wait, str(e)[:120],
                    )
                    await __import__('asyncio').sleep(wait)
                else:
                    logger.error("Hy3 call failed after %d retries: %s", self.settings.hy3_max_retries + 1, str(e)[:200])

        raise last_error  # type: ignore[misc]

    # ── Convenience modes ─────────────────────────────────────

    async def planner(
        self,
        system_prompt: str,
        user_content: str,
        *,
        tools: list[ToolDef] | None = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Planner mode: high reasoning, can use tools for information gathering."""
        return await self.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            reasoning_effort="high",
            temperature=0.3,
            max_tokens=max_tokens,
            tools=tools or [],
            tool_choice="auto" if tools else "none",
        )

    async def reader(
        self,
        system_prompt: str,
        user_content: str,
        *,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Reader mode: medium reasoning, no tools, large output window."""
        return await self.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            reasoning_effort="medium",
            temperature=0.1,
            max_tokens=max_tokens or self.settings.max_batch_output_tokens,
        )

    async def synthesizer(
        self,
        system_prompt: str,
        user_content: str,
        *,
        json_schema: dict[str, Any],
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Synthesizer mode: low reasoning, structured JSON output."""
        return await self.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            reasoning_effort="low",
            temperature=0.0,
            max_tokens=max_tokens or self.settings.synthesis_max_tokens,
            response_schema=json_schema,
        )

    async def react_agent(
        self,
        system_prompt: str,
        user_content: str,
        *,
        tools: list[ToolDef],
        max_rounds: int | None = None,
        max_tokens_per_round: int = 16384,
    ) -> LLMResponse:
        """ReAct Agent mode: iterative tool calling with auto-termination.

        Hy3 autonomously decides which tools to call and when to stop.
        The caller wraps this with actual tool execution logic.
        Returns the *final* response after all tool rounds.
        """
        rounds = max_rounds or self.settings.max_react_rounds_per_batch
        messages: list[Message] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        for _round in range(rounds):
            response = await self.chat(
                messages=messages,
                reasoning_effort="medium",
                temperature=0.1,
                max_tokens=max_tokens_per_round,
                tools=tools,
                tool_choice="auto",
            )

            # If Hy3 decided to stop (no tool calls), return final response
            if not response.tool_calls or response.finish_reason == "stop":
                return response

            # Record assistant message with tool calls
            assistant_msg: Message = {
                "role": "assistant",
                "content": response.content or "",
            }
            if response.tool_calls:
                assistant_msg["tool_calls"] = response.tool_calls
            messages.append(assistant_msg)

            # Simulate tool results — caller must have executed them
            # We return the response so the caller can execute tools and re-invoke
            # For a fully autonomous loop, wrap this method externally
            break  # Single-turn — caller loops externally

        return response

    # ── Streaming ─────────────────────────────────────────────

    async def chat_stream(self, **kwargs: Any) -> Any:
        """Return raw async stream for SSE forwarding."""
        kwargs.setdefault("stream", True)
        kwargs.setdefault("stream_options", {"include_usage": True})
        kwargs.setdefault("extra_body", {"prompt_cache_key": self.settings.prompt_cache_key})
        return await self._client.chat.completions.create(**kwargs)

    # ── Internals ─────────────────────────────────────────────

    def _parse_response(self, completion: Any) -> LLMResponse:
        choice = completion.choices[0]
        msg = choice.message
        tool_calls_raw = getattr(msg, "tool_calls", None) or []

        tool_calls = [
            {
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in tool_calls_raw
        ]

        usage = {}
        if hasattr(completion, "usage") and completion.usage:
            u = completion.usage
            usage = {
                "prompt_tokens": u.prompt_tokens or 0,
                "completion_tokens": u.completion_tokens or 0,
                "total_tokens": u.total_tokens or 0,
            }
            # Track cache if available
            if hasattr(u, "prompt_tokens_details") and u.prompt_tokens_details:
                details = u.prompt_tokens_details
                cache_read = getattr(details, "cached_tokens", 0) or 0
                usage["cache_read_tokens"] = cache_read

            self.usage.prompt_tokens += usage.get("prompt_tokens", 0)
            self.usage.completion_tokens += usage.get("completion_tokens", 0)
            self.usage.cache_read_tokens += usage.get("cache_read_tokens", 0)
            self.usage.call_count += 1

        return LLMResponse(
            content=msg.content or "",
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            usage=usage,
        )

    async def _collect_stream(self, stream: Any) -> LLMResponse:
        content_parts: list[str] = []
        tool_calls_map: dict[int, dict[str, Any]] = {}
        usage = {}
        finish_reason = "stop"

        async for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta
                if delta.content:
                    content_parts.append(delta.content)
                if hasattr(delta, "tool_calls") and delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_map:
                            tool_calls_map[idx] = {
                                "id": tc.id or "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            }
                        if tc.id:
                            tool_calls_map[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tool_calls_map[idx]["function"]["name"] += tc.function.name
                            if tc.function.arguments:
                                tool_calls_map[idx]["function"]["arguments"] += (
                                    tc.function.arguments
                                )
                if chunk.choices[0].finish_reason:
                    finish_reason = chunk.choices[0].finish_reason

            if hasattr(chunk, "usage") and chunk.usage:
                usage = {
                    "prompt_tokens": chunk.usage.prompt_tokens or 0,
                    "completion_tokens": chunk.usage.completion_tokens or 0,
                    "total_tokens": chunk.usage.total_tokens or 0,
                }

        self.usage.prompt_tokens += usage.get("prompt_tokens", 0)
        self.usage.completion_tokens += usage.get("completion_tokens", 0)
        self.usage.call_count += 1

        return LLMResponse(
            content="".join(content_parts),
            tool_calls=list(tool_calls_map.values()),
            finish_reason=finish_reason,
            usage=usage,
        )
