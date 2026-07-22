# ruff: noqa: RUF001
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from replaylab.schemas import MAX_TOTAL_INPUT_BYTES, TaskSpec

MAX_PROVIDER_OUTPUT_BYTES = 128_000


class FixtureNotFoundError(LookupError):
    pass


class FixtureAssetError(RuntimeError):
    pass


class FixtureSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixture_id: str
    title: str
    description: str
    domain: str


_FIXTURES = {
    "coding-loop": FixtureSummary(
        fixture_id="coding-loop",
        title="编程循环",
        description="新约束失败后，修复智能体仍重复只处理边缘的修改。",
        domain="代码任务",
    ),
    "research-grounding": FixtureSummary(
        fixture_id="research-grounding",
        title="研究证据漂移",
        description="研究智能体把相关关系升级为缺乏证据的因果结论。",
        domain="研究任务",
    ),
}


class FixtureStore:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def list(self) -> list[FixtureSummary]:
        return list(_FIXTURES.values())

    def load_task(self, fixture_id: str) -> TaskSpec:
        return TaskSpec.model_validate(
            self._read_json(fixture_id, "input.json", MAX_TOTAL_INPUT_BYTES)
        )

    def load_provider_output(self, fixture_id: str) -> dict[str, Any]:
        payload = self._read_json(
            fixture_id,
            "provider-output.json",
            MAX_PROVIDER_OUTPUT_BYTES,
        )
        if not isinstance(payload, dict):
            raise FixtureAssetError("built-in provider output must be a JSON object")
        return payload

    def _read_json(self, fixture_id: str, filename: str, byte_limit: int) -> Any:
        if fixture_id not in _FIXTURES:
            raise FixtureNotFoundError("unknown built-in fixture")
        path = (self._root / fixture_id / filename).resolve()
        if not path.is_relative_to(self._root):
            raise FixtureNotFoundError("unknown built-in fixture")
        try:
            raw = path.read_bytes()
        except OSError as error:
            raise FixtureAssetError("built-in fixture asset is unavailable") from error
        if len(raw) > byte_limit:
            raise FixtureAssetError("built-in fixture asset exceeds its byte budget")
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise FixtureAssetError("built-in fixture asset is invalid") from error
