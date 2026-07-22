import asyncio
import json
from pathlib import Path

import pytest

from replaylab import ReplayLabService, TaskSpec
from replaylab.service import ProviderOutputError

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_json(relative_path: str) -> dict[str, object]:
    return json.loads((PROJECT_ROOT / relative_path).read_text(encoding="utf-8"))


class RepairingProvider:
    name = "repairing-fake"
    model = "offline-fixture"
    mode = "fake"

    def __init__(self, repaired: dict[str, object]) -> None:
        self.repaired = repaired
        self.repair_calls = 0
        self.failure_codes: list[str] = []

    async def analyze(self, task: TaskSpec) -> str:
        del task
        return "{not valid JSON"

    async def repair(
        self,
        task: TaskSpec,
        invalid_output: object,
        failure_code: str,
    ) -> dict[str, object]:
        del task, invalid_output
        self.failure_codes.append(failure_code)
        self.repair_calls += 1
        return self.repaired


@pytest.mark.asyncio
async def test_invalid_provider_json_gets_exactly_one_controlled_repair() -> None:
    task = TaskSpec.model_validate(load_json("fixtures/coding-loop/input.json"))
    provider = RepairingProvider(load_json("fixtures/coding-loop/provider-output.json"))

    report = await ReplayLabService(provider).analyze(task)

    assert report.finding.first_divergence_step_id == "step-006-repeat-patch"
    assert provider.repair_calls == 1
    assert provider.failure_codes == [
        "schema_or_reference_validation_failed:invalid_json_or_schema"
    ]


class RecordingProvider(RepairingProvider):
    def __init__(self, response: dict[str, object]) -> None:
        super().__init__(response)
        self.seen_task: TaskSpec | None = None

    async def analyze(self, task: TaskSpec) -> dict[str, object]:
        self.seen_task = task
        return self.repaired


@pytest.mark.asyncio
async def test_credentials_are_redacted_before_provider_and_report() -> None:
    secret = "TOPSECRET123456"
    payload = load_json("fixtures/coding-loop/input.json")
    payload["evidence"][3]["content"] += f" Authorization: Bearer {secret}"
    task = TaskSpec.model_validate(payload)
    provider = RecordingProvider(load_json("fixtures/coding-loop/provider-output.json"))

    report = await ReplayLabService(provider).analyze(task)

    assert provider.seen_task is not None
    provider_payload = provider.seen_task.model_dump_json()
    report_payload = report.model_dump_json()
    assert secret not in provider_payload
    assert secret not in report_payload
    assert "[REDACTED]" in provider_payload
    assert "[REDACTED]" in report_payload


@pytest.mark.asyncio
async def test_credentials_echoed_by_provider_are_redacted_from_report() -> None:
    secret = "MODELLEAK123456"
    task = TaskSpec.model_validate(load_json("fixtures/coding-loop/input.json"))
    output = load_json("fixtures/coding-loop/provider-output.json")
    output["finding"]["explanation"] += f" password={secret}"

    report = await ReplayLabService(RecordingProvider(output)).analyze(task)

    serialized = report.model_dump_json()
    assert secret not in serialized
    assert "password=[REDACTED]" in serialized


class AlwaysInvalidProvider(RepairingProvider):
    async def repair(
        self,
        task: TaskSpec,
        invalid_output: object,
        failure_code: str,
    ) -> str:
        del task, invalid_output, failure_code
        self.repair_calls += 1
        return "still not JSON"


@pytest.mark.asyncio
async def test_failed_repair_is_rejected_after_exactly_one_attempt() -> None:
    task = TaskSpec.model_validate(load_json("fixtures/coding-loop/input.json"))
    provider = AlwaysInvalidProvider(load_json("fixtures/coding-loop/provider-output.json"))

    with pytest.raises(ProviderOutputError, match="failed controlled repair"):
        await ReplayLabService(provider).analyze(task)

    assert provider.repair_calls == 1


@pytest.mark.asyncio
async def test_unknown_output_reference_triggers_controlled_repair() -> None:
    task = TaskSpec.model_validate(load_json("fixtures/coding-loop/input.json"))
    valid = load_json("fixtures/coding-loop/provider-output.json")
    invalid = json.loads(json.dumps(valid))
    invalid["finding"]["evidence_ids"] = ["ev-unknown"]

    class UnknownReferenceProvider(RepairingProvider):
        async def analyze(self, task: TaskSpec) -> dict[str, object]:
            del task
            return invalid

    provider = UnknownReferenceProvider(valid)
    report = await ReplayLabService(provider).analyze(task)

    assert provider.repair_calls == 1
    assert provider.failure_codes == [
        "schema_or_reference_validation_failed:unknown_reference"
    ]
    assert report.finding.first_divergence_step_id == "step-006-repeat-patch"


@pytest.mark.asyncio
async def test_future_evidence_cannot_justify_the_first_divergence() -> None:
    task = TaskSpec.model_validate(load_json("fixtures/coding-loop/input.json"))
    invalid = load_json("fixtures/coding-loop/provider-output.json")
    invalid["finding"]["evidence_ids"] = ["ev-second-failure"]

    provider = RecordingProvider(invalid)
    with pytest.raises(ProviderOutputError, match="failed controlled repair"):
        await ReplayLabService(provider).analyze(task)

    assert provider.failure_codes == [
        "schema_or_reference_validation_failed:finding_evidence_after_divergence"
    ]


@pytest.mark.asyncio
async def test_impact_steps_must_follow_the_first_divergence() -> None:
    task = TaskSpec.model_validate(load_json("fixtures/coding-loop/input.json"))
    invalid = load_json("fixtures/coding-loop/provider-output.json")
    invalid["finding"]["impact_step_ids"] = ["step-004-patch-trim"]

    with pytest.raises(ProviderOutputError, match="failed controlled repair"):
        await ReplayLabService(RecordingProvider(invalid)).analyze(task)


@pytest.mark.asyncio
async def test_impact_steps_must_follow_timeline_order() -> None:
    task = TaskSpec.model_validate(load_json("fixtures/coding-loop/input.json"))
    invalid = load_json("fixtures/coding-loop/provider-output.json")
    invalid["finding"]["impact_step_ids"] = [
        "step-008-dangerous-suggestion",
        "step-007-repeat-test",
    ]

    with pytest.raises(ProviderOutputError, match="failed controlled repair"):
        await ReplayLabService(RecordingProvider(invalid)).analyze(task)


@pytest.mark.asyncio
async def test_a_divergence_requires_at_least_one_replay_action() -> None:
    task = TaskSpec.model_validate(load_json("fixtures/coding-loop/input.json"))
    invalid = load_json("fixtures/coding-loop/provider-output.json")
    invalid["replay_plan"]["actions"] = []

    with pytest.raises(ProviderOutputError, match="failed controlled repair"):
        await ReplayLabService(RecordingProvider(invalid)).analyze(task)


@pytest.mark.asyncio
async def test_a_no_divergence_plan_preserves_the_complete_trace() -> None:
    task = TaskSpec.model_validate(load_json("fixtures/coding-loop/input.json"))
    invalid = load_json("fixtures/coding-loop/provider-output.json")
    invalid["finding"].update(
        {
            "category": "no_divergence",
            "first_divergence_step_id": None,
            "impact_step_ids": [],
        }
    )
    invalid["replay_plan"].update(
        {
            "preserved_step_ids": [],
            "rerun_from_step_id": None,
            "rerun_step_ids": [],
            "actions": [],
        }
    )

    with pytest.raises(ProviderOutputError, match="failed controlled repair"):
        await ReplayLabService(RecordingProvider(invalid)).analyze(task)


@pytest.mark.asyncio
async def test_provider_cancellation_is_never_converted_into_a_repair() -> None:
    task = TaskSpec.model_validate(load_json("fixtures/coding-loop/input.json"))

    class CancelledProvider(RepairingProvider):
        async def analyze(self, task: TaskSpec) -> dict[str, object]:
            del task
            raise asyncio.CancelledError

    provider = CancelledProvider(load_json("fixtures/coding-loop/provider-output.json"))
    with pytest.raises(asyncio.CancelledError):
        await ReplayLabService(provider).analyze(task)

    assert provider.repair_calls == 0
