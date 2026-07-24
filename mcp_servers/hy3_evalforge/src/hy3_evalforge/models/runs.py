"""Input and artifact schemas for one evaluated JSONL run."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(pattern=r"^case_[0-9a-f]{16}$")
    output: str = Field(max_length=32_000)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class HardCheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_type: str
    passed: bool
    severity: str
    message: str
