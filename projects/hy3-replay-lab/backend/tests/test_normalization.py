import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from replaylab import TaskSpec

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_missing_identifiers_are_generated_stably_from_the_imported_timeline() -> None:
    payload = json.loads(
        (PROJECT_ROOT / "fixtures/coding-loop/input.json").read_text(encoding="utf-8")
    )
    for criterion in payload["criteria"]:
        criterion.pop("criterion_id")
    for step in payload["trace"]:
        step.pop("step_id")
        step["criterion_ids"] = []
        step["evidence_ids"] = []
    original_step_ids = {item["evidence_id"]: item["step_id"] for item in payload["evidence"]}
    source_sequences = {
        "step-001-intake": 1,
        "step-002-baseline": 2,
        "step-004-patch-trim": 4,
        "step-005-test-feedback": 5,
        "step-006-repeat-patch": 6,
        "step-007-repeat-test": 7,
        "step-008-dangerous-suggestion": 8,
    }
    for evidence in payload["evidence"]:
        evidence["step_sequence"] = source_sequences[original_step_ids[evidence["evidence_id"]]]
        evidence.pop("step_id")
        evidence.pop("evidence_id")

    first = TaskSpec.model_validate(copy.deepcopy(payload))
    second = TaskSpec.model_validate(copy.deepcopy(payload))

    assert [item.step_id for item in first.trace] == [item.step_id for item in second.trace]
    assert [item.evidence_id for item in first.evidence] == [
        item.evidence_id for item in second.evidence
    ]
    assert all(item.step_id.startswith("step_") for item in first.trace)
    assert all(item.evidence_id.startswith("evidence_") for item in first.evidence)
    assert all(item.step_sequence is None for item in first.evidence)


def test_aggregate_input_larger_than_the_budget_is_rejected() -> None:
    payload = {
        "schema_version": "1.0",
        "task": {"title": "Bounded import", "description": "Synthetic input budget test."},
        "criteria": [
            {
                "criterion_id": "criterion-budget",
                "title": "Stay bounded",
                "description": "The imported bundle stays within the documented byte limit.",
                "priority": "must",
            }
        ],
        "trace": [
            {
                "step_id": "step-001-input",
                "sequence": 1,
                "kind": "observation",
                "summary": "Imported a large synthetic bundle.",
                "details": "No operation is executed.",
                "status": "unknown",
                "criterion_ids": ["criterion-budget"],
                "evidence_ids": [],
            }
        ],
        "evidence": [
            {
                "evidence_id": f"evidence-{index:03}",
                "step_id": "step-001-input",
                "kind": "note",
                "source_label": "Synthetic budget input",
                "content": "x" * 4_500,
            }
            for index in range(60)
        ],
    }

    with pytest.raises(ValidationError, match="total input exceeds"):
        TaskSpec.model_validate(payload)


@pytest.mark.parametrize("failure", ["duplicate", "order", "unknown-reference"])
def test_trace_order_duplicate_ids_and_reference_closure_are_strict(failure: str) -> None:
    payload = json.loads(
        (PROJECT_ROOT / "fixtures/coding-loop/input.json").read_text(encoding="utf-8")
    )
    if failure == "duplicate":
        payload["trace"][1]["step_id"] = payload["trace"][0]["step_id"]
    elif failure == "order":
        payload["trace"][1]["sequence"] = 9
    else:
        payload["trace"][0]["criterion_ids"] = ["criterion-does-not-exist"]

    with pytest.raises(ValidationError):
        TaskSpec.model_validate(payload)


def test_boolean_values_are_not_coerced_into_trace_sequences() -> None:
    payload = json.loads(
        (PROJECT_ROOT / "fixtures/coding-loop/input.json").read_text(encoding="utf-8")
    )
    payload["trace"][0]["sequence"] = True

    with pytest.raises(ValidationError):
        TaskSpec.model_validate(payload)
