# Copyright (C) 2026 Tencent. Licensed under the Apache License, Version 2.0.
# SPDX-License-Identifier: Apache-2.0
"""Typed contracts between hyshell and the Hy3 model (strict JSON protocol).

The model must answer with **exactly one JSON object** (see the system prompts
in :mod:`hyshell.llm`). These pydantic models validate that contract; anything
else raises :class:`ModelOutputError` with a readable snippet of the raw text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class RiskLevel(IntEnum):
    """Risk grade of a shell command; ordered so ``max()`` = most severe."""

    SAFE = 0
    CAUTION = 1
    DANGEROUS = 2

    @property
    def label_zh(self) -> str:
        return {RiskLevel.SAFE: "安全", RiskLevel.CAUTION: "谨慎", RiskLevel.DANGEROUS: "危险"}[self]

    @property
    def label_en(self) -> str:
        return {RiskLevel.SAFE: "SAFE", RiskLevel.CAUTION: "CAUTION", RiskLevel.DANGEROUS: "DANGEROUS"}[self]

    @property
    def badge_style(self) -> str:
        """rich style for the risk badge."""
        return {
            RiskLevel.SAFE: "bold green",
            RiskLevel.CAUTION: "bold yellow",
            RiskLevel.DANGEROUS: "bold white on red",
        }[self]


def _parse_risk(value: object) -> RiskLevel:
    if isinstance(value, RiskLevel):
        return value
    if isinstance(value, int):
        return RiskLevel(value)
    if isinstance(value, str):
        try:
            return RiskLevel[value.strip().upper()]
        except KeyError as exc:
            raise ValueError(f"unknown risk level: {value!r}") from exc
    raise ValueError(f"unparseable risk level: {value!r}")


class CommandPlan(BaseModel):
    """Hy3's answer to a *plan* or *alt* task."""

    model_config = ConfigDict(extra="ignore")

    command: str
    explanation: str
    risk: RiskLevel
    risk_reasons: list[str] = []
    notes: Optional[str] = None

    @field_validator("risk", mode="before")
    @classmethod
    def _coerce_risk(cls, v: object) -> RiskLevel:
        return _parse_risk(v)

    @field_validator("command")
    @classmethod
    def _non_empty_command(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("command must be a non-empty string")
        return v.strip()


class FixSuggestion(BaseModel):
    """Hy3's answer to a *fix* task (error → repaired command)."""

    model_config = ConfigDict(extra="ignore")

    diagnosis: str
    command: str
    risk: RiskLevel
    risk_reasons: list[str] = []
    confidence: Literal["high", "medium", "low"] = "medium"

    @field_validator("risk", mode="before")
    @classmethod
    def _coerce_risk(cls, v: object) -> RiskLevel:
        return _parse_risk(v)

    @field_validator("command")
    @classmethod
    def _non_empty_command(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("command must be a non-empty string")
        return v.strip()


@dataclass
class ExecutionResult:
    """Outcome of actually running a command through the executor."""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_s: float
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


@dataclass
class TurnRecord:
    """One REPL turn, persisted to the JSONL history."""

    ts: str
    request: str
    command: Optional[str]
    source: Literal["plan", "fix", "alt", "edit", "none"]
    risk_final: Optional[RiskLevel]
    executed: bool
    exit_code: Optional[int]
    mode: str
    fix_attempts: int = 0
    blocked: bool = False
    notes: list[str] = field(default_factory=list)


class ModelOutputError(RuntimeError):
    """Raised when the model reply cannot be parsed into the JSON contract."""
