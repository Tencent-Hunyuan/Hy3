from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from replaylab.schemas import AnalysisDraft, TaskSpec

REDACTED = "[REDACTED]"
_CREDENTIAL_PATTERNS = (
    re.compile(r"(?i)(authorization\s*:\s*(?:bearer|token)\s+)[^\s,;]+"),
    re.compile(r"(?i)((?:api[_-]?key|token|password|secret|cookie)\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"(?i)\bsk-[a-z0-9_-]{8,}\b"),
    re.compile(r"(?i)([a-z][a-z0-9+.-]*://[^:\s/@]+:)[^@\s/]+(@)"),
)


def redact_task_spec(task: TaskSpec, *, secret_values: Sequence[str] = ()) -> TaskSpec:
    payload = _redact_value(task.model_dump(mode="json"), secret_values=secret_values)
    return TaskSpec.model_validate(payload)


def redact_analysis_draft(
    draft: AnalysisDraft, *, secret_values: Sequence[str] = ()
) -> AnalysisDraft:
    payload = _redact_value(draft.model_dump(mode="json"), secret_values=secret_values)
    return AnalysisDraft.model_validate(payload)


def redact_text(value: str, *, secret_values: Sequence[str] = ()) -> str:
    redacted = value
    for secret in secret_values:
        if secret:
            redacted = redacted.replace(secret, REDACTED)
    redacted = _CREDENTIAL_PATTERNS[0].sub(lambda match: match.group(1) + REDACTED, redacted)
    redacted = _CREDENTIAL_PATTERNS[1].sub(lambda match: match.group(1) + REDACTED, redacted)
    redacted = _CREDENTIAL_PATTERNS[2].sub(REDACTED, redacted)
    redacted = _CREDENTIAL_PATTERNS[3].sub(
        lambda match: match.group(1) + REDACTED + match.group(2), redacted
    )
    return redacted


def _redact_value(value: Any, *, secret_values: Sequence[str]) -> Any:
    if isinstance(value, str):
        return redact_text(value, secret_values=secret_values)
    if isinstance(value, Mapping):
        return {
            key: _redact_value(item, secret_values=secret_values) for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_value(item, secret_values=secret_values) for item in value]
    return value
