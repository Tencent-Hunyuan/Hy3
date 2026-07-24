"""Schemas and normalization for formal evaluation specifications."""

from __future__ import annotations

import math
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from hy3_evalforge.models.cases import HardCheck


class EvaluationDimension(BaseModel):
    """One weighted 0–4 semantic scoring dimension."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    description: str = Field(min_length=1, max_length=4_000)
    weight: float = Field(gt=0)
    anchors: dict[str, str]

    @field_validator("anchors")
    @classmethod
    def require_all_anchors(cls, anchors: dict[str, str]) -> dict[str, str]:
        if set(anchors) != {"0", "1", "2", "3", "4"} or not all(
            isinstance(value, str) and value.strip() for value in anchors.values()
        ):
            raise ValueError(
                "anchors must define non-empty descriptions for every score from 0 through 4"
            )
        return anchors


class RegressionPolicy(BaseModel):
    """Statistical decision thresholds that accompany every specification."""

    model_config = ConfigDict(extra="forbid")

    practical_delta: float = Field(default=3.0, gt=0)
    minimum_cases: int = Field(default=10, ge=1, le=50)


class EvalSpecDraft(BaseModel):
    """Hy3-designed specification before content normalization assigns its stable ID."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    goal: str = Field(min_length=1, max_length=32_000)
    dimensions: list[EvaluationDimension] = Field(min_length=1)
    hard_gates: list[HardCheck] = Field(default_factory=list)
    regression_policy: RegressionPolicy = Field(default_factory=RegressionPolicy)
    prompt_version: str = Field(default="judge-v1", min_length=1, max_length=128)

    @model_validator(mode="after")
    def unique_dimension_names(self) -> EvalSpecDraft:
        names = [dimension.name for dimension in self.dimensions]
        if len(set(names)) != len(names):
            raise ValueError("dimension names must be unique")
        return self


class EvalSpec(EvalSpecDraft):
    """A normalized, persisted specification with a content-derived ID."""

    spec_id: str = Field(pattern=r"^spec_[0-9a-f]{16}$")


class DesignSpecResult(BaseModel):
    """Structured result returned by `evalforge_design_spec`."""

    model_config = ConfigDict(extra="forbid")

    spec_id: str
    spec_path: str
    dimension_count: int
    hard_gate_count: int
    warnings: list[str] = Field(default_factory=list)


def normalize_dimension_weights(dimensions: list[EvaluationDimension]) -> list[EvaluationDimension]:
    """Normalize weights deterministically, with the final value closing the float sum at 1."""
    total = sum((Decimal(str(dimension.weight)) for dimension in dimensions), start=Decimal("0"))
    if total <= 0:
        raise ValueError("dimension weights must have a positive total")

    normalized: list[EvaluationDimension] = []
    for index, dimension in enumerate(dimensions):
        if index == len(dimensions) - 1:
            weight = 1.0 - math.fsum(item.weight for item in normalized)
        else:
            weight = float(Decimal(str(dimension.weight)) / total)
        normalized.append(dimension.model_copy(update={"weight": weight}))
    return normalized
