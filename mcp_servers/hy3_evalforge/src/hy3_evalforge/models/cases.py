"""Schemas for challenge cases and the restricted deterministic-check DSL."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class HardCheckType(StrEnum):
    """The complete non-executable hard-rule DSL allowed by the frozen design."""

    CONTAINS_ALL = "contains_all"
    CONTAINS_ANY = "contains_any"
    NOT_CONTAINS = "not_contains"
    REGEX_MATCH = "regex_match"
    VALID_JSON = "valid_json"
    JSON_SCHEMA = "json_schema"
    MAX_LENGTH = "max_length"
    REQUIRED_TOOL_CALLS = "required_tool_calls"
    FORBIDDEN_TOOL_CALLS = "forbidden_tool_calls"


class Severity(StrEnum):
    """A hard-rule failure severity that never changes semantic scoring."""

    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class HardCheck(BaseModel):
    """A declarative rule definition; it never contains executable user code."""

    model_config = ConfigDict(extra="forbid")

    type: HardCheckType
    value: Any = None
    severity: Severity = Severity.CRITICAL

    @model_validator(mode="after")
    def validate_value_shape(self) -> HardCheck:
        list_checks = {
            HardCheckType.CONTAINS_ALL,
            HardCheckType.CONTAINS_ANY,
            HardCheckType.REQUIRED_TOOL_CALLS,
            HardCheckType.FORBIDDEN_TOOL_CALLS,
        }
        string_checks = {HardCheckType.NOT_CONTAINS, HardCheckType.REGEX_MATCH}
        if self.type in list_checks and (
            not isinstance(self.value, list)
            or not all(isinstance(item, str) for item in self.value)
        ):
            raise ValueError(f"{self.type.value} requires a list of strings")
        if self.type in string_checks and not isinstance(self.value, str):
            raise ValueError(f"{self.type.value} requires a string")
        if self.type is HardCheckType.JSON_SCHEMA and not isinstance(self.value, dict):
            raise ValueError("json_schema requires an object")
        if self.type is HardCheckType.MAX_LENGTH and (
            not isinstance(self.value, int) or isinstance(self.value, bool) or self.value < 0
        ):
            raise ValueError("max_length requires a non-negative integer")
        if self.type is HardCheckType.VALID_JSON and self.value is not None:
            raise ValueError("valid_json does not accept a value")
        return self


class EvalCaseDraft(BaseModel):
    """A generated case before its stable ID is assigned."""

    model_config = ConfigDict(extra="forbid")

    input: str = Field(min_length=1, max_length=32_000)
    expected_behavior: str = Field(min_length=1, max_length=32_000)
    forbidden_behavior: str = Field(min_length=1, max_length=32_000)
    dimensions: list[str] = Field(min_length=1)
    hard_checks: list[HardCheck] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    risk_level: Severity = Severity.MAJOR
    weight: float = Field(default=1.0, gt=0)

    @field_validator("dimensions", "tags")
    @classmethod
    def unique_nonempty_names(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if not all(normalized) or len(set(normalized)) != len(normalized):
            raise ValueError("values must be non-empty and unique")
        return normalized


class EvalCase(EvalCaseDraft):
    """A persisted challenge case with a stable, content-derived ID."""

    case_id: str = Field(pattern=r"^case_[0-9a-f]{16}$")


class CaseCoverage(BaseModel):
    """Coverage analysis persisted alongside the generated JSONL case collection."""

    model_config = ConfigDict(extra="forbid")

    dimension_cases: dict[str, list[str]]
    uncovered_dimensions: list[str] = Field(default_factory=list)
    duplicate_case_ids: list[str] = Field(default_factory=list)


class GenerateCasesResult(BaseModel):
    """Structured result returned by `evalforge_generate_cases`."""

    model_config = ConfigDict(extra="forbid")

    cases_path: str
    coverage_path: str
    case_count: int
    warnings: list[str] = Field(default_factory=list)
