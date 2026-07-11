"""Tests for eval/report.py: metrics arithmetic, gate check, markdown rendering.

All inputs are hand-built CommandCaseResult/DiffCaseResult lists — no corpus
parsing, no LLM calls.
"""

from __future__ import annotations

import pytest

from eval.report import GATE, check_gate, command_metrics, diff_metrics, render_markdown_report
from eval.runner import AttackSurface, CommandCaseResult, CommandKind, DiffCaseResult, DiffKind
from hy3_security_mcp.schemas import AuditLevel, FindingSeverity, SecurityCategory


def _cmd_result(
    id_: str,
    kind: CommandKind,
    category: SecurityCategory,
    attack_surface: AttackSurface,
    expected_level: AuditLevel,
    actual_level: AuditLevel | None,
    correct: bool,
    source: str = "llm",
    expected_category: SecurityCategory | None = None,
    actual_category: SecurityCategory | None = None,
    error: str | None = None,
) -> CommandCaseResult:
    return CommandCaseResult(
        id=id_,
        category=category,
        attack_surface=attack_surface,
        kind=kind,
        expected_level=expected_level,
        actual_level=actual_level,
        expected_category=expected_category,
        actual_category=actual_category,
        correct=correct,
        source=source,
        error=error,
    )


class TestCommandMetrics:
    def test_overall_detection_and_fp_rates_are_exact(self) -> None:
        results = [
            _cmd_result(
                "d1",
                "danger",
                SecurityCategory.DESTRUCTIVE_FS,
                "direct",
                AuditLevel.DENY,
                AuditLevel.DENY,
                True,
            ),
            _cmd_result(
                "d2",
                "danger",
                SecurityCategory.DESTRUCTIVE_FS,
                "direct",
                AuditLevel.DENY,
                AuditLevel.ALLOW,
                False,
            ),
            _cmd_result(
                "d3",
                "danger",
                SecurityCategory.DESTRUCTIVE_FS,
                "direct",
                AuditLevel.CONFIRM,
                AuditLevel.CONFIRM,
                True,
            ),
            _cmd_result(
                "s1",
                "safe",
                SecurityCategory.DESTRUCTIVE_FS,
                "direct",
                AuditLevel.ALLOW,
                AuditLevel.ALLOW,
                True,
            ),
            _cmd_result(
                "s2",
                "safe",
                SecurityCategory.DESTRUCTIVE_FS,
                "direct",
                AuditLevel.ALLOW,
                AuditLevel.CONFIRM,
                False,
            ),
        ]

        metrics = command_metrics(results)

        assert metrics["overall"]["danger_total"] == 3
        assert metrics["overall"]["danger_caught"] == 2
        assert metrics["overall"]["detection_rate"] == pytest.approx(2 / 3)
        assert metrics["overall"]["safe_total"] == 2
        assert metrics["overall"]["safe_misflagged"] == 1
        assert metrics["overall"]["fp_rate"] == pytest.approx(0.5)

    def test_per_category_and_per_surface_breakdowns(self) -> None:
        results = [
            _cmd_result(
                "d1",
                "danger",
                SecurityCategory.DESTRUCTIVE_FS,
                "direct",
                AuditLevel.DENY,
                AuditLevel.DENY,
                True,
            ),
            _cmd_result(
                "d2",
                "danger",
                SecurityCategory.SENSITIVE_FILE,
                "prompt_injection",
                AuditLevel.CONFIRM,
                AuditLevel.ALLOW,
                False,
            ),
        ]

        metrics = command_metrics(results)

        assert metrics["by_category"]["destructive_fs"]["detection_rate"] == pytest.approx(1.0)
        assert metrics["by_category"]["sensitive_file"]["detection_rate"] == pytest.approx(0.0)
        assert metrics["by_attack_surface"]["direct"]["danger_total"] == 1
        assert metrics["by_attack_surface"]["prompt_injection"]["danger_caught"] == 0

    def test_matrix_cell_is_caught_over_total(self) -> None:
        results = [
            _cmd_result(
                "d1",
                "danger",
                SecurityCategory.DESTRUCTIVE_FS,
                "direct",
                AuditLevel.DENY,
                AuditLevel.DENY,
                True,
            ),
            _cmd_result(
                "d2",
                "danger",
                SecurityCategory.DESTRUCTIVE_FS,
                "direct",
                AuditLevel.DENY,
                AuditLevel.ALLOW,
                False,
            ),
        ]

        metrics = command_metrics(results)

        cell = metrics["matrix"]["destructive_fs"]["direct"]
        assert cell["total"] == 2
        assert cell["caught"] == 1
        assert cell["detection_rate"] == pytest.approx(0.5)

    def test_empty_results_do_not_divide_by_zero(self) -> None:
        metrics = command_metrics([])

        assert metrics["overall"]["detection_rate"] == 0.0
        assert metrics["overall"]["fp_rate"] == 0.0

    def test_no_errors_summary_is_empty(self) -> None:
        results = [
            _cmd_result(
                "d1",
                "danger",
                SecurityCategory.DESTRUCTIVE_FS,
                "direct",
                AuditLevel.DENY,
                AuditLevel.DENY,
                True,
            ),
        ]

        metrics = command_metrics(results)

        assert metrics["errors"] == {"count": 0, "ids": []}

    def test_category_accuracy_counts_mismatch_over_caught_danger(self) -> None:
        """A caught danger case whose actual_category differs from its
        expected_category is a category miss — surfaced separately from the
        deny/confirm detection outcome (which stays `correct`)."""
        results = [
            _cmd_result(
                "d1",
                "danger",
                SecurityCategory.SENSITIVE_FILE,
                "direct",
                AuditLevel.CONFIRM,
                AuditLevel.CONFIRM,
                True,
                expected_category=SecurityCategory.SENSITIVE_FILE,
                actual_category=SecurityCategory.SENSITIVE_FILE,
            ),
            _cmd_result(
                "d2",
                "danger",
                SecurityCategory.SENSITIVE_FILE,
                "direct",
                AuditLevel.CONFIRM,
                AuditLevel.CONFIRM,
                True,
                expected_category=SecurityCategory.SENSITIVE_FILE,
                actual_category=SecurityCategory.DESTRUCTIVE_FS,  # caught, wrong category
            ),
        ]

        metrics = command_metrics(results)

        assert metrics["category_accuracy"]["total"] == 2
        assert metrics["category_accuracy"]["correct"] == 1
        assert metrics["category_accuracy"]["rate"] == pytest.approx(0.5)

    def test_category_accuracy_ignores_uncaught_and_errored_danger(self) -> None:
        """Only caught danger cases with a known actual_category are eligible —
        a missed case (wrong level) and an errored case (no actual_category)
        are excluded from the category-accuracy denominator."""
        results = [
            _cmd_result(
                "hit",
                "danger",
                SecurityCategory.SENSITIVE_FILE,
                "direct",
                AuditLevel.CONFIRM,
                AuditLevel.CONFIRM,
                True,
                expected_category=SecurityCategory.SENSITIVE_FILE,
                actual_category=SecurityCategory.SENSITIVE_FILE,
            ),
            _cmd_result(
                "missed",
                "danger",
                SecurityCategory.SENSITIVE_FILE,
                "direct",
                AuditLevel.CONFIRM,
                AuditLevel.ALLOW,
                False,
                expected_category=SecurityCategory.SENSITIVE_FILE,
                actual_category=None,
            ),
            _cmd_result(
                "errored",
                "danger",
                SecurityCategory.SENSITIVE_FILE,
                "direct",
                AuditLevel.CONFIRM,
                None,
                False,
                source="error",
                error="RuntimeError: boom",
                expected_category=SecurityCategory.SENSITIVE_FILE,
                actual_category=None,
            ),
        ]

        metrics = command_metrics(results)

        assert metrics["category_accuracy"]["total"] == 1
        assert metrics["category_accuracy"]["correct"] == 1
        assert metrics["category_accuracy"]["rate"] == pytest.approx(1.0)

    def test_errored_safe_case_is_excluded_from_fp_denominator(self) -> None:
        """An errored safe case scores `correct=True` (conservative), but must
        NOT sit in the FP denominator — the rate is over successfully-evaluated
        safe cases only, so a flaky endpoint cannot deflate the FP rate."""
        results = [
            _cmd_result(
                "s_ok",
                "safe",
                SecurityCategory.SENSITIVE_FILE,
                "direct",
                AuditLevel.ALLOW,
                AuditLevel.ALLOW,
                True,
            ),
            _cmd_result(
                "s_fp",
                "safe",
                SecurityCategory.SENSITIVE_FILE,
                "direct",
                AuditLevel.ALLOW,
                AuditLevel.CONFIRM,
                False,
            ),
            _cmd_result(
                "s_err",
                "safe",
                SecurityCategory.SENSITIVE_FILE,
                "direct",
                AuditLevel.ALLOW,
                None,
                True,
                source="error",
                error="RuntimeError: boom",
            ),
        ]

        metrics = command_metrics(results)

        assert metrics["overall"]["safe_total"] == 3
        assert metrics["overall"]["safe_evaluated"] == 2
        assert metrics["overall"]["safe_misflagged"] == 1
        # 1 false positive over 2 successfully-evaluated safe cases, not 3.
        assert metrics["overall"]["fp_rate"] == pytest.approx(0.5)

    def test_errors_summary_lists_errored_case_ids(self) -> None:
        results = [
            _cmd_result(
                "d1",
                "danger",
                SecurityCategory.DESTRUCTIVE_FS,
                "direct",
                AuditLevel.DENY,
                AuditLevel.DENY,
                True,
            ),
            _cmd_result(
                "d2",
                "danger",
                SecurityCategory.DESTRUCTIVE_FS,
                "direct",
                AuditLevel.DENY,
                None,
                False,
                source="error",
                error="RuntimeError: boom",
            ),
        ]

        metrics = command_metrics(results)

        assert metrics["errors"] == {"count": 1, "ids": ["d2"]}


def _diff_result(
    name: str,
    kind: DiffKind,
    correct: bool,
    expected_min_severity: FindingSeverity | None = None,
    detected: bool = False,
    max_severity: FindingSeverity | None = None,
    weakness_expected: str | None = None,
    error: str | None = None,
) -> DiffCaseResult:
    return DiffCaseResult(
        name=name,
        kind=kind,
        expected_min_severity=expected_min_severity,
        detected=detected,
        max_severity=max_severity,
        weakness_expected=weakness_expected,
        correct=correct,
        error=error,
    )


class TestDiffMetrics:
    def test_detection_and_fp_rates_are_exact(self) -> None:
        results = [
            _diff_result(
                "m1.diff",
                "malicious",
                True,
                expected_min_severity=FindingSeverity.HIGH,
                detected=True,
                max_severity=FindingSeverity.HIGH,
                weakness_expected="命令注入",
            ),
            _diff_result(
                "m2.diff",
                "malicious",
                False,
                expected_min_severity=FindingSeverity.HIGH,
                detected=False,
                max_severity=None,
                weakness_expected="SQL注入",
            ),
            _diff_result("b1.diff", "benign", True),
            _diff_result("b2.diff", "benign", False, max_severity=FindingSeverity.MEDIUM),
        ]

        metrics = diff_metrics(results)

        assert metrics["malicious_total"] == 2
        assert metrics["malicious_detected"] == 1
        assert metrics["detection_rate"] == pytest.approx(0.5)
        assert metrics["benign_total"] == 2
        assert metrics["benign_misflagged"] == 1
        assert metrics["fp_rate"] == pytest.approx(0.5)
        assert metrics["by_weakness"]["命令注入"]["detection_rate"] == pytest.approx(1.0)
        assert metrics["by_weakness"]["SQL注入"]["detection_rate"] == pytest.approx(0.0)

    def test_errored_benign_case_is_excluded_from_fp_denominator(self) -> None:
        """Same convention as command safe cases: an errored benign diff scores
        `correct=True` but is excluded from the FP denominator (rate over
        successfully-evaluated benign diffs only)."""
        results = [
            _diff_result("b_ok.diff", "benign", True),
            _diff_result("b_fp.diff", "benign", False, max_severity=FindingSeverity.MEDIUM),
            _diff_result("b_err.diff", "benign", True, error="RuntimeError: boom"),
        ]

        metrics = diff_metrics(results)

        assert metrics["benign_total"] == 3
        assert metrics["benign_evaluated"] == 2
        assert metrics["benign_misflagged"] == 1
        assert metrics["fp_rate"] == pytest.approx(0.5)

    def test_empty_results_do_not_divide_by_zero(self) -> None:
        metrics = diff_metrics([])

        assert metrics["detection_rate"] == 0.0
        assert metrics["fp_rate"] == 0.0

    def test_no_errors_summary_is_empty(self) -> None:
        results = [_diff_result("b1.diff", "benign", True)]

        metrics = diff_metrics(results)

        assert metrics["errors"] == {"count": 0, "ids": []}

    def test_errors_summary_lists_errored_case_names(self) -> None:
        results = [
            _diff_result(
                "m1.diff",
                "malicious",
                False,
                expected_min_severity=FindingSeverity.HIGH,
                error="RuntimeError: boom",
            ),
            _diff_result("b1.diff", "benign", True),
        ]

        metrics = diff_metrics(results)

        assert metrics["errors"] == {"count": 1, "ids": ["m1.diff"]}


class TestCheckGate:
    def test_passes_when_all_rates_within_gate(self) -> None:
        cmd_metrics = {"overall": {"detection_rate": 0.9, "fp_rate": 0.1}}
        dif_metrics = {"detection_rate": 0.85, "fp_rate": 0.05}

        passed, failing = check_gate(cmd_metrics, dif_metrics, GATE)

        assert passed is True
        assert failing == []

    def test_fails_and_lists_reasons_when_thresholds_missed(self) -> None:
        cmd_metrics = {"overall": {"detection_rate": 0.5, "fp_rate": 0.5}}
        dif_metrics = {"detection_rate": 0.9, "fp_rate": 0.05}

        passed, failing = check_gate(cmd_metrics, dif_metrics, GATE)

        assert passed is False
        assert len(failing) == 2
        assert any("detection_rate" in reason for reason in failing)
        assert any("fp_rate" in reason for reason in failing)

    def test_all_safe_errored_makes_command_fp_inconclusive_not_pass(self) -> None:
        """When every safe command case errored (safe_evaluated == 0), fp_rate is
        a meaningless 0/0 = 0.0 — the gate must treat it as inconclusive/FAIL,
        never PASS on the vacuous rate."""
        cmd_metrics = {
            "overall": {
                "detection_rate": 1.0,
                "fp_rate": 0.0,
                "safe_total": 5,
                "safe_evaluated": 0,
            }
        }
        dif_metrics = {
            "detection_rate": 0.9,
            "fp_rate": 0.05,
            "benign_total": 3,
            "benign_evaluated": 3,
        }

        passed, failing = check_gate(cmd_metrics, dif_metrics, GATE)

        assert passed is False
        assert any("inconclusive" in reason for reason in failing)

    def test_all_benign_errored_makes_diff_fp_inconclusive_not_pass(self) -> None:
        cmd_metrics = {
            "overall": {
                "detection_rate": 1.0,
                "fp_rate": 0.0,
                "safe_total": 5,
                "safe_evaluated": 5,
            }
        }
        dif_metrics = {
            "detection_rate": 0.9,
            "fp_rate": 0.0,
            "benign_total": 3,
            "benign_evaluated": 0,
        }

        passed, failing = check_gate(cmd_metrics, dif_metrics, GATE)

        assert passed is False
        assert any("inconclusive" in reason for reason in failing)

    def test_exactly_at_threshold_passes(self) -> None:
        gate = {"detection_min": 0.80, "fp_max": 0.15}
        cmd_metrics = {"overall": {"detection_rate": 0.80, "fp_rate": 0.15}}
        dif_metrics = {"detection_rate": 0.80, "fp_rate": 0.15}

        passed, failing = check_gate(cmd_metrics, dif_metrics, gate)

        assert passed is True
        assert failing == []


class TestRenderMarkdownReport:
    def test_report_contains_matrix_headline_and_pass_line(self) -> None:
        cmd_metrics = {
            "overall": {
                "danger_total": 2,
                "danger_caught": 2,
                "detection_rate": 1.0,
                "safe_total": 1,
                "safe_evaluated": 1,
                "safe_misflagged": 0,
                "fp_rate": 0.0,
            },
            "by_category": {},
            "by_attack_surface": {},
            "category_accuracy": {"total": 2, "correct": 2, "rate": 1.0},
            "matrix": {
                "destructive_fs": {"direct": {"total": 2, "caught": 2, "detection_rate": 1.0}},
            },
            "errors": {"count": 0, "ids": []},
        }
        dif_metrics = {
            "malicious_total": 1,
            "malicious_detected": 1,
            "detection_rate": 1.0,
            "benign_total": 1,
            "benign_evaluated": 1,
            "benign_misflagged": 0,
            "fp_rate": 0.0,
            "by_weakness": {"命令注入": {"total": 1, "detected": 1, "detection_rate": 1.0}},
            "errors": {"count": 0, "ids": []},
        }

        report = render_markdown_report(cmd_metrics, dif_metrics, gate=GATE)

        assert "destructive_fs" in report
        assert "direct" in report
        assert "命令注入" in report
        assert "PASS" in report
        assert "FAIL" not in report
        assert "WARNING" not in report

    def test_report_shows_fail_line_and_reasons_when_gate_missed(self) -> None:
        cmd_metrics = {
            "overall": {
                "danger_total": 2,
                "danger_caught": 0,
                "detection_rate": 0.0,
                "safe_total": 1,
                "safe_evaluated": 1,
                "safe_misflagged": 1,
                "fp_rate": 1.0,
            },
            "by_category": {},
            "by_attack_surface": {},
            "category_accuracy": {"total": 2, "correct": 2, "rate": 1.0},
            "matrix": {},
            "errors": {"count": 0, "ids": []},
        }
        dif_metrics = {
            "malicious_total": 1,
            "malicious_detected": 0,
            "detection_rate": 0.0,
            "benign_total": 1,
            "benign_evaluated": 1,
            "benign_misflagged": 1,
            "fp_rate": 1.0,
            "by_weakness": {},
            "errors": {"count": 0, "ids": []},
        }

        report = render_markdown_report(cmd_metrics, dif_metrics, gate=GATE)

        assert "FAIL" in report

    def test_errors_line_and_warning_appear_when_command_case_errored(self) -> None:
        cmd_metrics = {
            "overall": {
                "danger_total": 2,
                "danger_caught": 2,
                "detection_rate": 1.0,
                "safe_total": 1,
                "safe_evaluated": 1,
                "safe_misflagged": 0,
                "fp_rate": 0.0,
            },
            "by_category": {},
            "by_attack_surface": {},
            "category_accuracy": {"total": 2, "correct": 2, "rate": 1.0},
            "matrix": {
                "destructive_fs": {"direct": {"total": 2, "caught": 2, "detection_rate": 1.0}},
            },
            "errors": {"count": 1, "ids": ["c2"]},
        }
        dif_metrics = {
            "malicious_total": 1,
            "malicious_detected": 1,
            "detection_rate": 1.0,
            "benign_total": 1,
            "benign_evaluated": 1,
            "benign_misflagged": 0,
            "fp_rate": 0.0,
            "by_weakness": {"命令注入": {"total": 1, "detected": 1, "detection_rate": 1.0}},
            "errors": {"count": 0, "ids": []},
        }

        report = render_markdown_report(cmd_metrics, dif_metrics, gate=GATE)

        assert "errors: 1" in report
        assert "c2" in report
        assert "WARNING" in report
        # the gate still computes PASS/FAIL on the rates even with errors present.
        assert "PASS" in report
