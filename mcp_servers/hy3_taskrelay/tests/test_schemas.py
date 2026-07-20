import pytest
from pydantic import ValidationError

from hy3_taskrelay.identifiers import stable_content_id
from hy3_taskrelay.schemas import (
    AuditCheckpointInput,
    AuditResult,
    Checkpoint,
    CreateCheckpointInput,
    CreateResumeBriefInput,
    ResumeDraft,
)


def test_checkpoint_input_rejects_duplicate_evidence_ids() -> None:
    evidence = {
        "evidence_id": "ev_test",
        "content": "The failing test is test_total.",
        "source": "synthetic test log",
    }

    with pytest.raises(ValidationError, match="evidence IDs must be unique"):
        CreateCheckpointInput(
            goal="Fix the interrupted bug.",
            session_material="The previous session reproduced the failure.",
            constraints=["Do not change the public API."],
            decisions=[],
            evidence=[evidence, evidence],
        )


def test_checkpoint_input_caps_total_material() -> None:
    evidence = [
        {
            "evidence_id": f"ev_{index}",
            "content": "x" * 4_000,
            "source": "synthetic fixture",
        }
        for index in range(5)
    ]

    with pytest.raises(ValidationError, match="total input exceeds 30000 characters"):
        CreateCheckpointInput(
            goal="g" * 2_000,
            session_material="s" * 12_000,
            constraints=[],
            decisions=[],
            evidence=evidence,
        )


def test_portable_checkpoint_rejects_unknown_evidence_references() -> None:
    payload = {
        "schema_version": "1.0",
        "goal": "Continue the fix.",
        "confirmed_facts": [{"text": "The test fails.", "evidence_ids": ["ev_missing"]}],
        "constraints": [],
        "decisions": [],
        "open_questions": [],
        "next_steps": [
            {
                "action": "Patch it.",
                "verification": "The test passes.",
                "evidence_ids": ["ev_log"],
            }
        ],
        "evidence": [{"evidence_id": "ev_log", "content": "failure", "source": "log"}],
    }
    payload["checkpoint_id"] = stable_content_id("cp", payload)

    with pytest.raises(ValidationError, match="unknown evidence IDs"):
        Checkpoint.model_validate(payload)


def _large_checkpoint(evidence_count: int) -> Checkpoint:
    evidence = [
        {
            "evidence_id": f"ev_{index}",
            "content": "x" * 4_000,
            "source": "synthetic fixture",
        }
        for index in range(evidence_count)
    ]
    payload = {
        "schema_version": "1.0",
        "goal": "Continue.",
        "confirmed_facts": [{"text": "Fact.", "evidence_ids": ["ev_0"]}],
        "constraints": [],
        "decisions": [],
        "open_questions": [],
        "next_steps": [{"action": "Continue.", "verification": "Done.", "evidence_ids": ["ev_0"]}],
        "evidence": evidence,
    }
    payload["checkpoint_id"] = stable_content_id("cp", payload)
    return Checkpoint.model_validate(payload)


def _large_additional_evidence(prefix: str) -> list[dict[str, str]]:
    return [
        {
            "evidence_id": f"ev_{prefix}_{index}",
            "content": "y" * 4_000,
            "source": "synthetic fixture",
        }
        for index in range(20)
    ]


def test_artifact_limits_keep_audit_and_resume_contracts_closed() -> None:
    checkpoint = _large_checkpoint(15)
    audit_request = AuditCheckpointInput(
        checkpoint=checkpoint,
        additional_evidence=_large_additional_evidence("audit"),
    )
    audit = AuditResult(
        schema_version="1.0",
        checkpoint_id=checkpoint.checkpoint_id,
        overall_status="clean",
        findings=[],
        evidence=[*checkpoint.evidence, *audit_request.additional_evidence],
    )

    resume_request = CreateResumeBriefInput(
        checkpoint=checkpoint,
        audit=audit,
        additional_evidence=_large_additional_evidence("resume"),
        continuation_context="z" * 4_000,
    )

    assert len(audit_request.additional_evidence) == 20
    assert len(resume_request.additional_evidence) == 20


def test_checkpoint_artifact_has_an_aggregate_character_limit() -> None:
    with pytest.raises(ValidationError, match="checkpoint exceeds 65000 characters"):
        _large_checkpoint(16)


def test_resume_rejects_audit_evidence_content_rewritten_under_the_same_id() -> None:
    checkpoint = _large_checkpoint(1)
    forged_evidence = checkpoint.evidence[0].model_copy(update={"content": "forged content"})
    audit = AuditResult(
        schema_version="1.0",
        checkpoint_id=checkpoint.checkpoint_id,
        overall_status="clean",
        findings=[],
        evidence=[forged_evidence],
    )

    with pytest.raises(ValidationError, match="unchanged checkpoint evidence"):
        CreateResumeBriefInput(checkpoint=checkpoint, audit=audit)


def test_resume_draft_requires_evidence_for_model_authored_prohibitions() -> None:
    with pytest.raises(ValidationError):
        ResumeDraft.model_validate(
            {
                "concise_context": [{"text": "Known context.", "evidence_ids": ["ev_log"]}],
                "next_steps": [
                    {
                        "priority": 1,
                        "action": "Continue.",
                        "validation": "Done.",
                        "evidence_ids": ["ev_log"],
                    }
                ],
                "blockers": [],
                "do_not": [{"text": "Invented prohibition.", "evidence_ids": []}],
            }
        )
