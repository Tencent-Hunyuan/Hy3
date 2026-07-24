"""Safe evaluator for the finite hard-rule DSL; it never executes user-provided code."""

from __future__ import annotations

import json
import re
from typing import Any

import jsonschema

from hy3_evalforge.models.cases import HardCheck, HardCheckType
from hy3_evalforge.models.runs import HardCheckResult


def evaluate(
    checks: list[HardCheck], output: str, tool_calls: list[dict[str, Any]]
) -> list[HardCheckResult]:
    """Evaluate every declarative check deterministically against one candidate response."""
    return [_evaluate_one(check, output, tool_calls) for check in checks]


def _evaluate_one(
    check: HardCheck, output: str, tool_calls: list[dict[str, Any]]
) -> HardCheckResult:
    passed = False
    try:
        match check.type:
            case HardCheckType.CONTAINS_ALL:
                passed = all(value in output for value in check.value)
            case HardCheckType.CONTAINS_ANY:
                passed = any(value in output for value in check.value)
            case HardCheckType.NOT_CONTAINS:
                passed = check.value not in output
            case HardCheckType.REGEX_MATCH:
                passed = re.search(check.value, output) is not None
            case HardCheckType.VALID_JSON:
                json.loads(output)
                passed = True
            case HardCheckType.JSON_SCHEMA:
                jsonschema.validate(json.loads(output), check.value)
                passed = True
            case HardCheckType.MAX_LENGTH:
                passed = len(output) <= check.value
            case HardCheckType.REQUIRED_TOOL_CALLS:
                passed = set(check.value).issubset(_tool_names(tool_calls))
            case HardCheckType.FORBIDDEN_TOOL_CALLS:
                passed = not set(check.value).intersection(_tool_names(tool_calls))
    except (json.JSONDecodeError, jsonschema.ValidationError, re.error, TypeError):
        passed = False
    return HardCheckResult(
        check_type=check.type.value,
        passed=passed,
        severity=check.severity.value,
        message="passed" if passed else "failed",
    )


def _tool_names(tool_calls: list[dict[str, Any]]) -> set[str]:
    return {call["name"] for call in tool_calls if isinstance(call.get("name"), str)}
