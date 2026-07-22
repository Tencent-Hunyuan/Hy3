"""Typed tool results and internal findings."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["critical", "high", "medium", "low", "info"]
ChangeKind = Literal["breaking", "warning", "compatible"]


class Usage(BaseModel):
    """Token usage reported by the model provider."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class Finding(BaseModel):
    """One deterministic or model-assisted OpenAPI audit finding."""

    severity: Severity
    category: str
    location: str
    message: str
    suggestion: str
    source: Literal["local", "hy3"] = "local"


class AuditResult(BaseModel):
    """Structured result returned by audit_openapi."""

    tool: Literal["audit_openapi"] = "audit_openapi"
    specification: str
    openapi_version: str
    operation_count: int
    local_findings: list[Finding]
    hy3_analysis: str
    model: str
    usage: Usage = Field(default_factory=Usage)


class ApiChange(BaseModel):
    """One normalized difference between two OpenAPI specifications."""

    kind: ChangeKind
    category: str
    location: str
    message: str


class BreakingChangeResult(BaseModel):
    """Structured result returned by detect_breaking_changes."""

    tool: Literal["detect_breaking_changes"] = "detect_breaking_changes"
    old_specification: str
    new_specification: str
    breaking_count: int
    warning_count: int
    compatible_count: int
    changes: list[ApiChange]
    hy3_migration_analysis: str
    model: str
    usage: Usage = Field(default_factory=Usage)


class ContractTestResult(BaseModel):
    """Structured result returned by generate_contract_tests."""

    tool: Literal["generate_contract_tests"] = "generate_contract_tests"
    specification: str
    framework: Literal["pytest", "jest"]
    selected_operations: list[str]
    generated_code: str
    run_instructions: list[str]
    model: str
    usage: Usage = Field(default_factory=Usage)
