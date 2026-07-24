"""Schemas for Hy3 semantic judgments and aggregate scorecards."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: str
    quote: str = Field(min_length=1, max_length=32_000)
    explanation: str = Field(min_length=1, max_length=4_000)


class SingleJudgment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(pattern=r"^case_[0-9a-f]{16}$")
    dimension_scores: dict[str, int]
    evidence: list[Evidence]

    @field_validator("dimension_scores")
    @classmethod
    def scores_are_anchored(cls, scores: dict[str, int]) -> dict[str, int]:
        if not scores or any(score not in range(5) for score in scores.values()):
            raise ValueError("dimension scores must be integers from 0 through 4")
        return scores


class ScoreRunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_name: str
    scorecard_path: str
    run_score: float
    critical_failures: int
    manual_review_cases: list[str] = Field(default_factory=list)
