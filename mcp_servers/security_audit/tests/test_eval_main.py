"""Tests for eval/__main__.py's console summary.

`format_console_summary` is the pure helper `main()` prints — the ONLY live
signal a judge running `make eval` (= `python -m eval`) sees, since there's no
CI yet. These tests pin the honesty-critical formatting (errors must surface on
the console, never just in report.md) without touching the network path in
`main()`.
"""

from __future__ import annotations

from typing import Any

from eval.__main__ import format_console_summary


def _cmd_metrics(
    *, detection: float = 1.0, fp: float = 0.0, errors: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "overall": {"detection_rate": detection, "fp_rate": fp},
        "errors": errors or {"count": 0, "ids": []},
    }


def _diff_metrics(
    *, detection: float = 1.0, fp: float = 0.0, errors: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "detection_rate": detection,
        "fp_rate": fp,
        "errors": errors or {"count": 0, "ids": []},
    }


class TestFormatConsoleSummary:
    def test_clean_run_has_no_error_warning(self) -> None:
        summary = format_console_summary(_cmd_metrics(), _diff_metrics(), (True, []))

        assert "command: detection=100.0%" in summary
        assert "diff: detection=100.0%" in summary
        assert "PASS" in summary
        assert "⚠" not in summary
        assert "errored" not in summary

    def test_errored_command_cases_surface_warning_and_ids(self) -> None:
        cmd = _cmd_metrics(errors={"count": 2, "ids": ["c2", "c5"]})

        summary = format_console_summary(cmd, _diff_metrics(), (True, []))

        assert "⚠" in summary
        assert "2" in summary
        assert "errored" in summary
        assert "c2" in summary
        assert "c5" in summary
        # the gate verdict is still present, but a bare PASS is no longer alone.
        assert "PASS" in summary

    def test_errored_diff_cases_surface_warning_and_ids(self) -> None:
        diff = _diff_metrics(errors={"count": 1, "ids": ["bad.diff"]})

        summary = format_console_summary(_cmd_metrics(), diff, (True, []))

        assert "⚠" in summary
        assert "bad.diff" in summary
        assert "errored" in summary

    def test_fail_verdict_and_errors_coexist(self) -> None:
        cmd = _cmd_metrics(detection=0.0, errors={"count": 1, "ids": ["c1"]})

        summary = format_console_summary(
            cmd,
            _diff_metrics(),
            (False, ["command detection_rate 0.0% < gate 80.0%"]),
        )

        assert "FAIL" in summary
        assert "command detection_rate" in summary
        assert "⚠" in summary
        assert "c1" in summary
