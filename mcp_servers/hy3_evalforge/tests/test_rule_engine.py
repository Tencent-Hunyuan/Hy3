from hy3_evalforge.core.rule_engine import evaluate
from hy3_evalforge.models.cases import HardCheck, HardCheckType, Severity


def test_rule_engine_handles_safe_dsl_without_executing_input() -> None:
    checks = [
        HardCheck(
            type=HardCheckType.NOT_CONTAINS, value="INTERNAL_ONLY", severity=Severity.CRITICAL
        ),
        HardCheck(type=HardCheckType.VALID_JSON),
        HardCheck(type=HardCheckType.REQUIRED_TOOL_CALLS, value=["lookup"]),
    ]

    result = evaluate(checks, '{"answer":"safe"}', [{"name": "lookup"}])

    assert [item.passed for item in result] == [True, True, True]


def test_invalid_regex_fails_closed() -> None:
    result = evaluate([HardCheck(type=HardCheckType.REGEX_MATCH, value="[")], "anything", [])

    assert result[0].passed is False
