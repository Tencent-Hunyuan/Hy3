"""Run stable, offline TaskRelay evaluations over public synthetic fixtures."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from hy3_taskrelay.schemas import (
    AuditCheckpointInput,
    CreateCheckpointInput,
    CreateResumeBriefInput,
)
from hy3_taskrelay.service import TaskRelayService


class FixtureProvider:
    """Return fixture-authored model responses through the production service path."""

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self._responses = [json.dumps(response) for response in responses]

    async def complete(self, messages: list[dict[str, str]]) -> str:
        return self._responses.pop(0)


def _pointer(document: Any, pointer: str) -> Any:
    if pointer == "/":
        return document
    value = document
    for part in pointer.strip("/").split("/"):
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def _references(value: Any) -> set[str]:
    if isinstance(value, dict):
        current = set(value.get("evidence_ids", []))
        return current | set().union(*(_references(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(_references(item) for item in value))
    return set()


def _evaluate(operator: str, actual: Any, expected: Any, known_ids: set[str]) -> bool:
    if operator == "equals":
        return actual == expected
    if operator == "contains":
        return isinstance(actual, str) and expected in actual
    if operator == "set_equals":
        return set(actual) == set(expected)
    if operator == "length":
        return len(actual) == expected
    if operator == "refs_known":
        return _references(actual) <= known_ids
    if operator == "priorities_sorted":
        priorities = [item["priority"] for item in actual]
        return priorities == sorted(priorities) and len(priorities) == len(set(priorities))
    raise ValueError(f"Unknown evaluation operator: {operator}")


async def _artifacts(fixture: dict[str, Any]) -> dict[str, Any]:
    responses = fixture["hy3_responses"]
    service = TaskRelayService(
        FixtureProvider([responses["checkpoint"], responses["audit"], responses["resume"]])
    )
    checkpoint = await service.create_checkpoint(
        CreateCheckpointInput.model_validate(fixture["create_input"])
    )
    audit = await service.audit_checkpoint(
        AuditCheckpointInput(
            checkpoint=checkpoint,
            additional_evidence=fixture["additional_evidence"],
        )
    )
    resume = await service.create_resume_brief(
        CreateResumeBriefInput(
            checkpoint=checkpoint,
            audit=audit,
            continuation_context=fixture["continuation_context"],
        )
    )
    return {
        "checkpoint": checkpoint.model_dump(mode="json"),
        "audit": audit.model_dump(mode="json"),
        "resume": resume.model_dump(mode="json"),
    }


async def run_evaluations(project_root: Path) -> list[dict[str, Any]]:
    """Return one pass/fail record per independent evaluation case."""

    fixtures = {}
    for path in sorted((project_root / "examples" / "fixtures").glob("*.json")):
        fixture = json.loads(path.read_text(encoding="utf-8"))
        fixtures[fixture["fixture_id"]] = fixture
    cases = json.loads((project_root / "evals" / "cases.json").read_text(encoding="utf-8"))
    artifacts = {fixture_id: await _artifacts(fixture) for fixture_id, fixture in fixtures.items()}
    results = []
    for case in cases:
        fixture = fixtures[case["fixture"]]
        known_ids = {
            item["evidence_id"]
            for item in [
                *fixture["create_input"]["evidence"],
                *fixture["additional_evidence"],
            ]
        }
        actual = _pointer(artifacts[case["fixture"]][case["artifact"]], case["pointer"])
        passed = _evaluate(case["operator"], actual, case["expected"], known_ids)
        results.append({"case_id": case["case_id"], "passed": passed})
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    arguments = parser.parse_args()
    results = asyncio.run(run_evaluations(arguments.project_root))
    failed = [result for result in results if not result["passed"]]
    print(json.dumps({"total": len(results), "failed": failed}, ensure_ascii=False))
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
