"""Scriptable fake provider for deterministic unit and stdio integration tests."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from hy3_evalforge.errors import ErrorCode, EvalForgeError
from hy3_evalforge.providers.base import ProviderRequest, ProviderResponse


class FakeProvider:
    """Return scripted responses in order and record only request metadata by default."""

    def __init__(
        self, scripted_responses: Iterable[str | Exception], *, record_requests: bool = False
    ) -> None:
        self._scripted_responses = deque(scripted_responses)
        self.request_count = 0
        self.reasoning_efforts: list[str] = []
        self._record_requests = record_requests
        if record_requests:
            self.requests: list[ProviderRequest] = []

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        """Serve one scripted response; never persist prompts or candidate output."""
        self.request_count += 1
        self.reasoning_efforts.append(request.reasoning_effort)
        if self._record_requests:
            self.requests.append(request)
        if not self._scripted_responses:
            raise EvalForgeError(
                ErrorCode.PROVIDER_ERROR,
                "Fake provider has no scripted response remaining.",
            )
        result = self._scripted_responses.popleft()
        if isinstance(result, Exception):
            raise result
        return ProviderResponse(content=result)
