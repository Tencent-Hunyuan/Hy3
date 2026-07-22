from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
from pathlib import Path

from replaylab.evaluation import (
    EvaluationOutcome,
    EvaluationScenario,
    EvaluationSuite,
    build_golden_draft,
    build_task,
    evaluate_suite,
    load_evaluation_suite,
    render_evaluation_markdown,
)
from replaylab.hy3 import Hy3Provider, Hy3ProviderError, Hy3Settings
from replaylab.resources import default_result_root, evaluation_root
from replaylab.schemas import AnalysisDraft
from replaylab.service import ProviderOutputError, ReplayLabService
from replaylab.validation import OutputValidationError


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run ReplayLab's public synthetic evaluation suite."
    )
    parser.add_argument(
        "--mode", choices=("offline-golden-contract", "live-hy3"), required=True
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for the aggregate JSON and Markdown report.",
    )
    arguments = parser.parse_args()
    suite = load_evaluation_suite(evaluation_root())
    run_time = datetime.now(UTC)
    if arguments.mode == "offline-golden-contract":
        outcomes = _offline_outcomes(suite)
        model = "deterministic-golden-draft"
    else:
        settings = Hy3Settings.from_env()
        outcomes = asyncio.run(_live_outcomes(suite, settings))
        model = settings.model

    metrics = evaluate_suite(suite, outcomes)
    destination = arguments.output_dir or default_result_root()
    destination.mkdir(parents=True, exist_ok=True)
    stem = f"{arguments.mode}-{run_time.date().isoformat()}"
    json_path = destination / f"{stem}.json"
    markdown_path = destination / f"{stem}.md"
    json_path.write_text(metrics.model_dump_json(indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(
        render_evaluation_markdown(
            metrics,
            mode=arguments.mode,
            model=model,
            run_date=run_time.date().isoformat(),
        ),
        encoding="utf-8",
    )
    print(f"evaluation complete: {metrics.case_count} cases")
    print(f"structured success: {metrics.structured_success_rate:.3f}")
    print(f"report: {markdown_path}")


def _offline_outcomes(suite: EvaluationSuite) -> list[EvaluationOutcome]:
    annotations = {item.case_id: item for item in suite.annotations}
    return [
        EvaluationOutcome(
            case_id=scenario.case_id,
            draft=build_golden_draft(scenario, annotations[scenario.case_id]),
        )
        for scenario in suite.scenarios
    ]


async def _live_outcomes(
    suite: EvaluationSuite, settings: Hy3Settings
) -> list[EvaluationOutcome]:
    semaphore = asyncio.Semaphore(2)

    async def run_case(scenario: EvaluationScenario) -> EvaluationOutcome:
        async with semaphore:
            try:
                async with asyncio.timeout(90), Hy3Provider(settings) as provider:
                    report = await ReplayLabService(provider).analyze(
                        build_task(scenario)
                    )
                outcome = EvaluationOutcome(
                    case_id=scenario.case_id,
                    draft=AnalysisDraft(
                        coverage=report.coverage,
                        finding=report.finding,
                        replay_plan=report.replay_plan,
                    ),
                    prompt_tokens=report.metadata.prompt_tokens or 0,
                    completion_tokens=report.metadata.completion_tokens or 0,
                    total_tokens=report.metadata.total_tokens or 0,
                    latency_ms=report.metadata.latency_ms or 0,
                )
            except TimeoutError:
                outcome = EvaluationOutcome(
                    case_id=scenario.case_id,
                    draft=None,
                    error_code="evaluation_timeout",
                )
            except Hy3ProviderError:
                outcome = EvaluationOutcome(
                    case_id=scenario.case_id,
                    draft=None,
                    error_code="provider_request_failed",
                )
            except (ProviderOutputError, OutputValidationError):
                outcome = EvaluationOutcome(
                    case_id=scenario.case_id,
                    draft=None,
                    error_code="structured_output_rejected",
                )
            print(f"completed evaluation case: {scenario.case_id}")
            return outcome

    return list(await asyncio.gather(*(run_case(item) for item in suite.scenarios)))
