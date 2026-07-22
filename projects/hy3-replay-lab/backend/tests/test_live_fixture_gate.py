import json
from pathlib import Path

import pytest

from replaylab import ReplayLabService, StaticProvider, TaskSpec
from replaylab.cli_live_fixtures import _score_fixture_report

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_json(relative_path: str) -> dict[str, object]:
    return json.loads((PROJECT_ROOT / relative_path).read_text(encoding="utf-8"))


@pytest.mark.asyncio
@pytest.mark.parametrize("fixture_id", ["coding-loop", "research-grounding"])
async def test_fixture_gate_checks_the_complete_human_annotation(
    fixture_id: str,
) -> None:
    task = TaskSpec.model_validate(load_json(f"fixtures/{fixture_id}/input.json"))
    provider_output = load_json(f"fixtures/{fixture_id}/provider-output.json")
    annotation = load_json(f"fixtures/{fixture_id}/annotation.json")
    report = await ReplayLabService(StaticProvider(provider_output)).analyze(task)

    result = _score_fixture_report(annotation, report)

    assert result["passed"] is True
    assert result["first_divergence_correct"] is True
    assert result["constraint_preservation"] == 1
    assert result["required_evidence_coverage"] == 1
    assert result["replay_precision"] == 1
    assert result["replay_recall"] == 1
    assert result["validation_gate_coverage"] == 1
    assert result["dangerous_suggestion"] is False


@pytest.mark.asyncio
async def test_fixture_gate_rejects_a_report_that_only_gets_the_first_step_right() -> None:
    task = TaskSpec.model_validate(load_json("fixtures/coding-loop/input.json"))
    provider_output = load_json("fixtures/coding-loop/provider-output.json")
    annotation = load_json("fixtures/coding-loop/annotation.json")
    report = await ReplayLabService(StaticProvider(provider_output)).analyze(task)
    missing_evidence = "ev-repeat-diff"
    report.finding.evidence_ids.remove(missing_evidence)
    for coverage in report.coverage:
        if missing_evidence in coverage.evidence_ids:
            coverage.evidence_ids.remove(missing_evidence)
    for action in report.replay_plan.actions:
        if missing_evidence in action.evidence_ids:
            action.evidence_ids.remove(missing_evidence)
        if missing_evidence in action.validation_gate.evidence_ids:
            action.validation_gate.evidence_ids.remove(missing_evidence)
        if "criterion-regression" in action.validation_gate.criterion_ids:
            action.validation_gate.criterion_ids.remove("criterion-regression")
    for gate in report.replay_plan.stop_conditions:
        if "criterion-regression" in gate.criterion_ids:
            gate.criterion_ids.remove("criterion-regression")
    report.replay_plan.rerun_step_ids.append("step-001-intake")
    report.replay_plan.actions[0].action = annotation["dangerous_recommendations"][0]

    result = _score_fixture_report(annotation, report)

    assert result["first_divergence_correct"] is True
    assert result["passed"] is False
    assert result["required_evidence_coverage"] < 1
    assert result["replay_precision"] < 1
    assert result["validation_gate_coverage"] < 1
    assert result["dangerous_suggestion"] is True


@pytest.mark.asyncio
async def test_fixture_gate_requires_evidence_on_the_divergence_finding() -> None:
    task = TaskSpec.model_validate(load_json("fixtures/coding-loop/input.json"))
    provider_output = load_json("fixtures/coding-loop/provider-output.json")
    annotation = load_json("fixtures/coding-loop/annotation.json")
    report = await ReplayLabService(StaticProvider(provider_output)).analyze(task)
    report.finding.evidence_ids.remove("ev-repeat-diff")

    result = _score_fixture_report(annotation, report)

    assert result["required_evidence_coverage"] == pytest.approx(2 / 3)
    assert result["passed"] is False


@pytest.mark.asyncio
async def test_fixture_gate_normalizes_dangerous_suggestion_punctuation() -> None:
    task = TaskSpec.model_validate(load_json("fixtures/coding-loop/input.json"))
    provider_output = load_json("fixtures/coding-loop/provider-output.json")
    annotation = load_json("fixtures/coding-loop/annotation.json")
    report = await ReplayLabService(StaticProvider(provider_output)).analyze(task)
    report.replay_plan.actions[0].action = annotation[
        "dangerous_recommendations"
    ][0].removesuffix("。")

    result = _score_fixture_report(annotation, report)

    assert result["dangerous_suggestion"] is True
    assert result["passed"] is False
