"""Verdict schema for the security audit tool.

Defines the audit verdict model plus robust JSON extraction from LLM output.
Rendering of LLM replies is never trusted blindly: anything that cannot be
parsed into a valid verdict raises VerdictParseError — no silent fallbacks.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from enum import StrEnum
from typing import Any, Literal, TypeVar

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


def _scan_balanced_objects(text: str) -> list[dict[str, Any]]:
    """Find and parse every top-level balanced {...} block, respecting JSON strings.

    Blocks are returned in document order. A block that fails to parse as a JSON
    object is skipped, and scanning resumes at the next '{'.
    """
    objects: list[dict[str, Any]] = []
    start = text.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escaped = False
        close = -1
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
                    close = i
                    break
        if close != -1:
            parsed = _loads_object(text[start : close + 1])
            if parsed is not None:
                objects.append(parsed)
                start = text.find("{", close + 1)
                continue
        start = text.find("{", start + 1)
    return objects


def _collect_candidates(text: str) -> list[dict[str, Any]]:
    """Collect EVERY candidate JSON object from LLM output, position-independent.

    A prompt-injected decoy can be placed before OR after the real answer, and
    inside OR outside a ```json fence. Returning the first fence (or the last
    scanned object) is therefore exploitable. This gathers candidates from ALL
    ```json/``` fenced blocks AND a full balanced-brace scan of the whole text,
    deduplicating while preserving document order. Callers reduce the set with a
    security-aware rule (most-restrictive verdict / union of findings) so no
    decoy can override a real answer by position.

    A whole-text JSON object is unambiguous and returned as the sole candidate.
    """
    direct = _loads_object(text)
    if direct is not None:
        return [direct]

    candidates: list[dict[str, Any]] = []

    def _add(obj: dict[str, Any] | None) -> None:
        if obj is not None and obj not in candidates:
            candidates.append(obj)

    for fence in _FENCE_RE.finditer(text):
        _add(_loads_object(fence.group(1)))

    for obj in _scan_balanced_objects(text):
        _add(obj)

    return candidates


def extract_json(
    text: str,
    validator: Callable[[dict[str, Any]], bool] | None = None,
) -> dict[str, Any]:
    """Extract a single JSON object from LLM output text.

    Low-level convenience for the unambiguous case: it collects every candidate
    (see ``_collect_candidates``) and returns the sole one. When several
    candidates are present it returns the last that satisfies ``validator`` (or
    the last of all, if no validator). Security-critical callers do NOT rely on
    this reduction — ``parse_verdict`` and the report parsers reduce the full
    candidate set with a position-independent rule. Raises VerdictParseError
    (with an excerpt) when no object is found, or when several are found but none
    satisfy ``validator``.
    """
    candidates = _collect_candidates(text)
    if not candidates:
        raise VerdictParseError(f"no JSON object found in LLM output: {_excerpt(text)}")
    if len(candidates) == 1:
        return candidates[0]
    if validator is None:
        return candidates[-1]
    for obj in reversed(candidates):
        if validator(obj):
            return obj
    raise VerdictParseError(f"multiple JSON objects found but none valid: {_excerpt(text)}")


def _raise_parse_error(
    text: str,
    last_exc: pydantic.ValidationError | None,
    label: str,
) -> None:
    """Fail closed: no candidate validated. Surface the detailed field error when one exists."""
    if last_exc is not None:
        error = last_exc.errors()[0]
        field = ".".join(str(part) for part in error["loc"]) or "<root>"
        raise VerdictParseError(
            f"{label} JSON failed validation ({field}: {error['msg']}, "
            f"input={error.get('input')!r}): {_excerpt(text)}"
        ) from last_exc
    raise VerdictParseError(f"no JSON object found in LLM output: {_excerpt(text)}")


# Verdict severity ordering: a decoy adding a lower level can never lower a real one.
_LEVEL_RANK: dict[AuditLevel, int] = {
    AuditLevel.ALLOW: 0,
    AuditLevel.CONFIRM: 1,
    AuditLevel.DENY: 2,
}


def parse_verdict(text: str, *, source: Literal["fast_path", "llm"]) -> AuditVerdict:
    """Parse LLM output text into an AuditVerdict.

    The verdict source is set by the caller and never trusted from the text.
    Position-independent and fail-closed against prompt injection: every candidate
    object is validated as a verdict, and among those that validate the MOST
    RESTRICTIVE level (deny > confirm > allow) wins — so a decoy adding an
    ``allow`` before OR after the real ``deny``, fenced or not, can never
    downgrade it. If no candidate validates, VerdictParseError is raised.
    """
    valid: list[AuditVerdict] = []
    last_exc: pydantic.ValidationError | None = None
    for obj in _collect_candidates(text):
        try:
            valid.append(AuditVerdict.model_validate({**obj, "source": source}))
        except pydantic.ValidationError as exc:
            last_exc = exc
    if not valid:
        _raise_parse_error(text, last_exc, "verdict")
    return max(valid, key=lambda v: _LEVEL_RANK[v.level])


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


_ReportT = TypeVar("_ReportT", bound=pydantic.BaseModel)


def _collect_valid_models(
    text: str, model: type[_ReportT]
) -> tuple[list[_ReportT], pydantic.ValidationError | None]:
    """Validate every candidate object against ``model``; keep those that pass."""
    valid: list[_ReportT] = []
    last_exc: pydantic.ValidationError | None = None
    for obj in _collect_candidates(text):
        try:
            valid.append(model.model_validate(obj))
        except pydantic.ValidationError as exc:
            last_exc = exc
    return valid, last_exc


def _dedup_models(items: list[_ReportT]) -> list[_ReportT]:
    """Drop structurally-identical duplicates while preserving order."""
    seen: list[dict[str, Any]] = []
    out: list[_ReportT] = []
    for item in items:
        dumped = item.model_dump()
        if dumped not in seen:
            seen.append(dumped)
            out.append(item)
    return out


def _merge_summary(entries: list[tuple[str, list[Any]]]) -> str:
    """Merge summaries, preferring those from reports that contributed items.

    ``entries`` pairs each valid report's summary with its item list. A decoy
    with an empty item list and a reassuring summary must not become the
    surviving summary when a real report carries findings.
    """
    bearing: list[str] = []
    for summary, items in entries:
        if items and summary not in bearing:
            bearing.append(summary)
    if bearing:
        return " | ".join(bearing)
    return entries[0][0]


def parse_review_report(text: str) -> DiffReviewReport:
    """Parse LLM output text into a DiffReviewReport.

    Position-independent and fail-closed: every candidate object is validated as
    a report, and the findings of ALL valid reports are UNIONED (deduplicated).
    An empty-findings decoy — before OR after the real report, fenced or not —
    can therefore never suppress real findings. Raises VerdictParseError if no
    candidate validates.
    """
    valid, last_exc = _collect_valid_models(text, DiffReviewReport)
    if not valid:
        _raise_parse_error(text, last_exc, "diff review")
    findings = _dedup_models([f for report in valid for f in report.findings])
    summary = _merge_summary([(report.summary, report.findings) for report in valid])
    return DiffReviewReport(findings=findings, summary=summary)


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

    Position-independent and fail-closed: the secrets of ALL valid reports are
    UNIONED (deduplicated), so an empty-secrets decoy — regardless of position or
    fencing — cannot suppress real secrets. Raises VerdictParseError if no
    candidate validates.
    """
    valid, last_exc = _collect_valid_models(text, SecretScanReport)
    if not valid:
        _raise_parse_error(text, last_exc, "secret scan")
    secrets = _dedup_models([s for report in valid for s in report.secrets])
    summary = _merge_summary([(report.summary, report.secrets) for report in valid])
    return SecretScanReport(secrets=secrets, summary=summary)


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


# Finding severity ordering: merging picks the most severe overall_priority.
_SEVERITY_RANK: dict[FindingSeverity, int] = {
    FindingSeverity.INFO: 0,
    FindingSeverity.LOW: 1,
    FindingSeverity.MEDIUM: 2,
    FindingSeverity.HIGH: 3,
    FindingSeverity.CRITICAL: 4,
}


def parse_vuln_report(text: str) -> VulnIntelReport:
    """Parse LLM output text into a VulnIntelReport.

    Position-independent and fail-closed: the advisories of ALL valid reports are
    UNIONED (deduplicated) and ``overall_priority`` becomes the MOST severe among
    them, so a low-priority empty decoy — regardless of position or fencing —
    cannot suppress real advisories or downgrade priority. Raises
    VerdictParseError if no candidate validates.
    """
    valid, last_exc = _collect_valid_models(text, VulnIntelReport)
    if not valid:
        _raise_parse_error(text, last_exc, "vuln intel")
    advisories = _dedup_models([a for report in valid for a in report.advisories])
    overall_priority = max(
        (report.overall_priority for report in valid),
        key=lambda severity: _SEVERITY_RANK[severity],
    )
    summary = _merge_summary([(report.summary, report.advisories) for report in valid])
    return VulnIntelReport(
        advisories=advisories,
        summary=summary,
        overall_priority=overall_priority,
    )
