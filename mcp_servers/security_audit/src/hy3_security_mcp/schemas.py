"""Verdict schema for the security audit tool.

Defines the audit verdict model plus robust JSON extraction from LLM output.
Rendering of LLM replies is never trusted blindly: anything that cannot be
parsed into a valid verdict raises VerdictParseError — no silent fallbacks.
"""

from __future__ import annotations

import json
import re
from enum import StrEnum
from typing import Any, Literal

import pydantic

_EXCERPT_LIMIT = 200

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


class AuditLevel(StrEnum):
    """Verdict severity: allow silently, require confirmation, or refuse."""

    ALLOW = "allow"
    CONFIRM = "confirm"
    DENY = "deny"


class SecurityCategory(StrEnum):
    """The 7 danger categories of the security policy corpus."""

    DESTRUCTIVE_FS = "destructive_fs"
    SENSITIVE_FILE = "sensitive_file"
    NETWORK_EXFIL = "network_exfil"
    PERSISTENCE = "persistence"
    BACKDOOR = "backdoor"
    SSH_KEYS = "ssh_keys"
    SUDOERS = "sudoers"


class AuditVerdict(pydantic.BaseModel):
    """A single adjudication of one shell command."""

    level: AuditLevel
    category: SecurityCategory | None
    rationale: str
    safer_alternative: str | None = None
    source: Literal["fast_path", "llm"]


class VerdictParseError(Exception):
    """Raised when LLM output cannot be parsed into a valid AuditVerdict."""


def _excerpt(text: str) -> str:
    return text[:_EXCERPT_LIMIT]


def _loads_object(candidate: str) -> dict[str, Any] | None:
    """json.loads that returns the value only if it is a JSON object."""
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _scan_balanced_object(text: str) -> dict[str, Any] | None:
    """Find and parse the first balanced {...} block, respecting JSON strings."""
    start = text.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escaped = False
        for i in range(start, len(text)):
            char = text[i]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
            elif char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    parsed = _loads_object(text[start : i + 1])
                    if parsed is not None:
                        return parsed
                    break
        start = text.find("{", start + 1)
    return None


def extract_json(text: str) -> dict[str, Any]:
    """Extract a JSON object from LLM output text.

    Tries, in order: direct parse, ```json fenced block, first balanced
    {...} block. Raises VerdictParseError (with an excerpt) if none works.
    """
    direct = _loads_object(text)
    if direct is not None:
        return direct

    fence_match = _FENCE_RE.search(text)
    if fence_match:
        fenced = _loads_object(fence_match.group(1))
        if fenced is not None:
            return fenced

    scanned = _scan_balanced_object(text)
    if scanned is not None:
        return scanned

    raise VerdictParseError(f"no JSON object found in LLM output: {_excerpt(text)}")


def parse_verdict(text: str, *, source: Literal["fast_path", "llm"]) -> AuditVerdict:
    """Parse LLM output text into an AuditVerdict.

    The verdict source is set by the caller and never trusted from the text.
    Any validation failure is wrapped into VerdictParseError with an excerpt.
    """
    data = extract_json(text)
    data["source"] = source
    try:
        return AuditVerdict.model_validate(data)
    except pydantic.ValidationError as exc:
        error = exc.errors()[0]
        field = ".".join(str(part) for part in error["loc"]) or "<root>"
        raise VerdictParseError(
            f"verdict JSON failed validation ({field}: {error['msg']}, "
            f"input={error.get('input')!r}): {_excerpt(text)}"
        ) from exc


class FindingSeverity(StrEnum):
    """Severity of one security finding surfaced by the diff-review tool."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class SecurityFinding(pydantic.BaseModel):
    """One security weakness found in a reviewed diff."""

    severity: FindingSeverity
    title: str
    file: str | None = None
    line: int | None = None
    weakness: str
    detail: str
    fix_suggestion: str | None = None


class DiffReviewReport(pydantic.BaseModel):
    """The full result of one review_diff invocation."""

    findings: list[SecurityFinding]
    summary: str


def parse_review_report(text: str) -> DiffReviewReport:
    """Parse LLM output text into a DiffReviewReport.

    Reuses extract_json for JSON extraction; any validation failure is
    wrapped into VerdictParseError with the same excerpt discipline as
    parse_verdict.
    """
    data = extract_json(text)
    try:
        return DiffReviewReport.model_validate(data)
    except pydantic.ValidationError as exc:
        error = exc.errors()[0]
        field = ".".join(str(part) for part in error["loc"]) or "<root>"
        raise VerdictParseError(
            f"diff review JSON failed validation ({field}: {error['msg']}, "
            f"input={error.get('input')!r}): {_excerpt(text)}"
        ) from exc


class SecretVerdict(pydantic.BaseModel):
    """Hy3's triage of one local secret-scanner candidate."""

    line: int
    kind: str
    is_true_positive: bool
    severity: FindingSeverity
    rationale: str
    remediation: str | None = None


class SecretScanReport(pydantic.BaseModel):
    """The full result of one scan_secrets invocation."""

    secrets: list[SecretVerdict]
    summary: str


def parse_secret_report(text: str) -> SecretScanReport:
    """Parse LLM output text into a SecretScanReport.

    Reuses extract_json for JSON extraction; any validation failure is
    wrapped into VerdictParseError with the same excerpt discipline as
    parse_verdict/parse_review_report.
    """
    data = extract_json(text)
    try:
        return SecretScanReport.model_validate(data)
    except pydantic.ValidationError as exc:
        error = exc.errors()[0]
        field = ".".join(str(part) for part in error["loc"]) or "<root>"
        raise VerdictParseError(
            f"secret scan JSON failed validation ({field}: {error['msg']}, "
            f"input={error.get('input')!r}): {_excerpt(text)}"
        ) from exc


class VulnAdvisory(pydantic.BaseModel):
    """Hy3's synthesized advisory for one known vulnerability from OSV.dev."""

    vuln_id: str
    severity: FindingSeverity
    affected: str
    exploitability: str
    remediation: str
    references: list[str] = []


class VulnIntelReport(pydantic.BaseModel):
    """The full result of one vuln_intel invocation."""

    advisories: list[VulnAdvisory]
    summary: str
    overall_priority: FindingSeverity


def parse_vuln_report(text: str) -> VulnIntelReport:
    """Parse LLM output text into a VulnIntelReport.

    Reuses extract_json for JSON extraction; any validation failure is
    wrapped into VerdictParseError with the same excerpt discipline as
    parse_verdict/parse_review_report/parse_secret_report.
    """
    data = extract_json(text)
    try:
        return VulnIntelReport.model_validate(data)
    except pydantic.ValidationError as exc:
        error = exc.errors()[0]
        field = ".".join(str(part) for part in error["loc"]) or "<root>"
        raise VerdictParseError(
            f"vuln intel JSON failed validation ({field}: {error['msg']}, "
            f"input={error.get('input')!r}): {_excerpt(text)}"
        ) from exc
