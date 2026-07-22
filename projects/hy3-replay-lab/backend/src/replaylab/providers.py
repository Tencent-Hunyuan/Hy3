from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Protocol

from replaylab.schemas import TaskSpec


class AnalysisProvider(Protocol):
    name: str
    model: str
    mode: str

    async def analyze(self, task: TaskSpec) -> Mapping[str, Any] | str: ...

    async def repair(
        self,
        task: TaskSpec,
        invalid_output: Mapping[str, Any] | str,
        failure_code: str,
    ) -> Mapping[str, Any] | str: ...


class StaticProvider:
    """A deterministic provider used only at the external-model test boundary."""

    name = "static-fixture"
    model = "offline-fixture"
    mode = "fake"

    def __init__(self, response: Mapping[str, Any]) -> None:
        self._response = json.loads(json.dumps(response))

    async def analyze(self, task: TaskSpec) -> Mapping[str, Any]:
        del task
        return json.loads(json.dumps(self._response))

    async def repair(
        self,
        task: TaskSpec,
        invalid_output: Mapping[str, Any] | str,
        failure_code: str,
    ) -> Mapping[str, Any]:
        del task, invalid_output, failure_code
        return json.loads(json.dumps(self._response))
