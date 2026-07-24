"""Provider contract independent of the OpenAI-compatible Hy3 transport."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProviderRequest:
    """One model request, with untrusted data isolated in the user message."""

    system_prompt: str
    user_prompt: str
    reasoning_effort: str


@dataclass(frozen=True)
class ProviderResponse:
    """The raw model text; workflow services must validate it before use."""

    content: str


class Provider(Protocol):
    """Minimal interface used by all four EvalForge workflows."""

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        """Execute a single provider request without logging its content."""
