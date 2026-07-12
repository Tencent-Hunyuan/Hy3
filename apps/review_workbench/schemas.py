from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


MAX_DIFF_CHARS = 24_000


class ReviewPayload(BaseModel):
    patch_text: str = Field(max_length=MAX_DIFF_CHARS)
    language: str = Field(default="python", max_length=40)
    focus: str = Field(
        default="correctness, security, reliability, and tests",
        max_length=240,
    )
    context: str = Field(default="", max_length=1_000)

    @field_validator("patch_text")
    @classmethod
    def patch_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("patch_text must not be blank")
        return value


class TestPlanPayload(BaseModel):
    diff_text: str = Field(max_length=MAX_DIFF_CHARS)
    test_framework: str = Field(default="pytest", max_length=40)
    risk_level: Literal["low", "medium", "high", "critical"] = "medium"

    @field_validator("diff_text")
    @classmethod
    def diff_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("diff_text must not be blank")
        return value


class Hy3Response(BaseModel):
    content: str
    metadata: dict[str, Any]


class StatusResponse(BaseModel):
    ready: bool
    model: str
    endpoint: str
