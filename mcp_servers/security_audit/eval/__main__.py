"""CLI entrypoint: ``python -m eval`` (run from hy3-security-mcp/).

Loads Hy3Config, runs both evals against the full committed corpus
(eval/cases/), writes eval/report.md, prints the headline + gate verdict, and
exits non-zero when the gate fails — this is what makes the eval CI-usable.

This needs a live HY3_API_KEY (Task 9 wires it into CI). ``--offline``, or a
missing/invalid key, prints a clear message and exits WITHOUT attempting any
network call or raising a traceback.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

from eval.report import GATE, check_gate, command_metrics, diff_metrics, render_markdown_report
from eval.runner import (
    CommandCase,
    CommandCaseResult,
    DiffCase,
    DiffCaseResult,
    load_command_cases,
    load_diff_labels,
    run_command_eval,
    run_diff_eval,
)
from hy3_security_mcp.config import ConfigError, load_config
from hy3_security_mcp.hy3_client import Hy3Client, Hy3CompletionClient

_EVAL_DIR = Path(__file__).resolve().parent
_COMMANDS_DIR = _EVAL_DIR / "cases" / "commands"
_DIFFS_DIR = _EVAL_DIR / "cases" / "diffs"
_REPORT_PATH = _EVAL_DIR / "report.md"

# Exit codes: 0 = ran, gate passed. 1 = ran, gate failed (CI should fail the
# build). 2 = did NOT run at all (offline/no key) -- distinct from a gate
# failure so CI logs never conflate "no key configured" with "eval regressed".
_EXIT_PASS = 0
_EXIT_GATE_FAILED = 1
_EXIT_NOT_RUN = 2

_NEEDS_KEY_MESSAGE = (
    "eval needs a live HY3_API_KEY to call Hy3 (it exercises the real "
    "audit_command/review_diff tools end-to-end, not the FakeHy3Client test "
    "seam). Set HY3_API_KEY and re-run without --offline, or see .env.example."
)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m eval",
        description="Score audit_command/review_diff against the eval/cases corpus.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="skip the live-API eval and print the 'needs key' message instead of running",
    )
    return parser.parse_args(argv)


async def _run_evals(
    client: Hy3CompletionClient,
    command_cases: list[CommandCase],
    diff_cases: list[DiffCase],
) -> tuple[list[CommandCaseResult], list[DiffCaseResult]]:
    command_results = await run_command_eval(command_cases, client=client)
    diff_results = await run_diff_eval(diff_cases, client=client)
    return command_results, diff_results


def _errors_console_line(kind: str, errors: dict[str, Any]) -> str | None:
    """`⚠ N <kind> case(s) errored (not evaluated): id1, id2` — or None when
    that section had no errors. Errored cases were never evaluated; they're
    scored conservatively in the rates (see eval/runner.py) but MUST also show
    here so a partially-errored run can't print a bare PASS on the console."""
    if not errors["count"]:
        return None
    return f"⚠ {errors['count']} {kind} case(s) errored (not evaluated): {', '.join(errors['ids'])}"


def format_console_summary(
    cmd_metrics: dict[str, Any],
    diff_metrics: dict[str, Any],
    gate_result: tuple[bool, list[str]],
) -> str:
    """Build the multi-line console summary main() prints.

    This is the ONLY live signal a competition judge running `make eval` sees
    (no CI yet), so it must mirror report.md's error visibility: the rate line,
    then a ⚠ warning line per section that had errored cases (with their ids),
    then the PASS/FAIL verdict. Pure over already-computed metrics — no network.
    """
    passed, failing = gate_result
    lines = [
        f"command: detection={cmd_metrics['overall']['detection_rate']:.1%} "
        f"fp={cmd_metrics['overall']['fp_rate']:.1%} | "
        f"diff: detection={diff_metrics['detection_rate']:.1%} "
        f"fp={diff_metrics['fp_rate']:.1%}"
    ]
    for line in (
        _errors_console_line("command", cmd_metrics["errors"]),
        _errors_console_line("diff", diff_metrics["errors"]),
    ):
        if line is not None:
            lines.append(line)
    lines.append("PASS" if passed else "FAIL: " + "; ".join(failing))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args(argv)

    if args.offline:
        print(_NEEDS_KEY_MESSAGE)
        return _EXIT_NOT_RUN

    try:
        config = load_config()
    except ConfigError as exc:
        print(f"{_NEEDS_KEY_MESSAGE}\n({exc})")
        return _EXIT_NOT_RUN

    client = Hy3Client(config)
    command_cases = load_command_cases(str(_COMMANDS_DIR))
    diff_cases = load_diff_labels(str(_DIFFS_DIR))

    command_results, diff_results = asyncio.run(_run_evals(client, command_cases, diff_cases))

    cmd_metrics = command_metrics(command_results)
    dif_metrics = diff_metrics(diff_results)
    report_md = render_markdown_report(cmd_metrics, dif_metrics, gate=GATE)
    _REPORT_PATH.write_text(report_md, encoding="utf-8")

    passed, failing = check_gate(cmd_metrics, dif_metrics, GATE)
    print(f"report written to {_REPORT_PATH}")
    print(format_console_summary(cmd_metrics, dif_metrics, (passed, failing)))
    return _EXIT_PASS if passed else _EXIT_GATE_FAILED


if __name__ == "__main__":
    sys.exit(main())
