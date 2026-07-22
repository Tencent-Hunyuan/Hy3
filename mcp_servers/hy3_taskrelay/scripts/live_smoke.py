"""Run all three TaskRelay operations against the configured real Hy3 API."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import date
from pathlib import Path

from hy3_taskrelay.config import Settings
from hy3_taskrelay.hy3_client import REASONING_EFFORT, TEMPERATURE, TOP_P, Hy3Client
from hy3_taskrelay.schemas import (
    AuditCheckpointInput,
    CreateCheckpointInput,
    CreateResumeBriefInput,
)
from hy3_taskrelay.security import redact_data
from hy3_taskrelay.service import TaskRelayService


async def run(fixture_path: Path) -> dict[str, object]:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    settings = Settings.from_env()
    secret = settings.api_key.get_secret_value()
    service = TaskRelayService(Hy3Client(settings), secret_values=(secret,))
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
    record = {
        "date": date.today().isoformat(),
        "fixture_id": fixture["fixture_id"],
        "model": settings.model,
        "parameters": {
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "reasoning_effort": REASONING_EFFORT,
        },
        "checkpoint": {
            "checkpoint_id": checkpoint.checkpoint_id,
            "confirmed_fact_count": len(checkpoint.confirmed_facts),
            "next_step_count": len(checkpoint.next_steps),
        },
        "audit": {
            "overall_status": audit.overall_status,
            "finding_categories": [finding.category for finding in audit.findings],
        },
        "resume": {
            "resume_id": resume.resume_id,
            "priority_order": [step.priority for step in resume.next_steps],
        },
        "redaction": (
            "Only bounded metadata is recorded; prompts, raw responses, and "
            "credentials are omitted."
        ),
    }
    return redact_data(record, (secret,))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "examples"
        / "fixtures"
        / "interrupted_bug_fix.json",
    )
    arguments = parser.parse_args()
    print(json.dumps(asyncio.run(run(arguments.fixture)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
