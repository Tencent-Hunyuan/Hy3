"""Shared test doubles for Hy3-backed tools. Used by ALL task test suites."""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence

from hy3_security_mcp.hy3_client import ReasoningEffort


class FakeHy3Client:
    """Deterministic Hy3CompletionClient: replies from a queue, records calls.

    Structurally satisfies the Hy3CompletionClient protocol (no explicit
    inheritance needed).

    A queued item may be a reply string OR an Exception instance — an
    Exception is raised (instead of returned) when its turn comes up, letting
    tests inject a per-call error at a specific position in a multi-case run
    (e.g. eval/runner.py's per-case error handling) without the `error=`
    kwarg, which unconditionally raises on every call.
    """

    def __init__(
        self, replies: Sequence[str | Exception], *, error: Exception | None = None
    ) -> None:
        self._replies: deque[str | Exception] = deque(replies)
        self.error = error
        self.calls: list[tuple[str, str, ReasoningEffort]] = []

    async def complete(
        self, system: str, user: str, *, reasoning_effort: ReasoningEffort = "no_think"
    ) -> str:
        self.calls.append((system, user, reasoning_effort))
        if self.error is not None:
            raise self.error
        if not self._replies:
            raise AssertionError("FakeHy3Client.complete called but no replies remain queued")
        reply = self._replies.popleft()
        if isinstance(reply, Exception):
            raise reply
        return reply
