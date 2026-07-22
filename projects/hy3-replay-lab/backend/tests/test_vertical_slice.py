import json
from pathlib import Path

import pytest

from replaylab import ReplayLabService, StaticProvider, TaskSpec

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_json(relative_path: str) -> dict[str, object]:
    return json.loads((PROJECT_ROOT / relative_path).read_text(encoding="utf-8"))


@pytest.mark.asyncio
async def test_coding_loop_becomes_an_evidence_grounded_minimal_replay_report() -> None:
    task = TaskSpec.model_validate(load_json("fixtures/coding-loop/input.json"))
    provider_output = load_json("fixtures/coding-loop/provider-output.json")

    report = await ReplayLabService(StaticProvider(provider_output)).analyze(task)

    assert report.finding.first_divergence_step_id == "step-006-repeat-patch"
    assert report.finding.evidence_ids == [
        "ev-task-collapse",
        "ev-repeat-failure",
        "ev-repeat-diff",
    ]
    assert report.replay_plan.preserved_step_ids == [
        "step-001-intake",
        "step-002-baseline",
        "step-003-inspect",
        "step-004-patch-trim",
        "step-005-test-feedback",
    ]
    assert report.replay_plan.rerun_from_step_id == "step-006-repeat-patch"
    assert [action.order for action in report.replay_plan.actions] == [1, 2, 3]
    assert {item.criterion_id for item in report.coverage} == {
        "criterion-collapse",
        "criterion-trim",
        "criterion-regression",
    }
    assert report.report_id.startswith("report_")
