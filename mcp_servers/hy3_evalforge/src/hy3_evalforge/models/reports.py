"""Schemas for a baseline/candidate regression report."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ComparisonStatus(StrEnum):
    BLOCKED = "BLOCKED"
    REGRESSED = "REGRESSED"
    IMPROVED = "IMPROVED"
    NO_MATERIAL_CHANGE = "NO_MATERIAL_CHANGE"
    INCONCLUSIVE = "INCONCLUSIVE"


class CompareRunsResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ComparisonStatus
    report_path: str
    json_path: str
    confidence_interval: tuple[float, float] | None


class PairwiseEvidence(BaseModel):
    model_config = ConfigDict(extra="ignore")

    quote: str = Field(min_length=1, max_length=32_000)


class PairwiseJudgment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    winner: Literal["A", "B", "TIE"]
    evidence: list[PairwiseEvidence] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def convert_legacy_quote_list(cls, value):
        if isinstance(value, dict) and "evidence_quotes" in value and "evidence" not in value:
            value = {
                **value,
                "evidence": [{"quote": item} for item in value["evidence_quotes"]],
            }
        return value
