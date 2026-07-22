"""Pydantic contracts shared by the TaskRelay tools and MCP protocol."""

from __future__ import annotations

import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from hy3_taskrelay.identifiers import stable_content_id

EvidenceId = Annotated[
    str,
    Field(
        min_length=3,
        max_length=64,
        pattern=r"^ev_[A-Za-z0-9][A-Za-z0-9._-]*$",
        description="Caller-assigned stable evidence identifier beginning with ev_",
    ),
]
ShortText = Annotated[str, Field(min_length=1, max_length=1_000)]
EvidenceIds = Annotated[list[EvidenceId], Field(min_length=1, max_length=20)]
MAX_CHECKPOINT_INPUT_CHARACTERS = 30_000
MAX_CHECKPOINT_DRAFT_CHARACTERS = 30_000
MAX_CHECKPOINT_ARTIFACT_CHARACTERS = 65_000
MAX_AUDIT_INPUT_CHARACTERS = 200_000
MAX_AUDIT_DRAFT_CHARACTERS = 60_000
MAX_AUDIT_ARTIFACT_CHARACTERS = 300_000
MAX_RESUME_INPUT_CHARACTERS = 500_000
MAX_RESUME_DRAFT_CHARACTERS = 60_000
MAX_RESUME_ARTIFACT_CHARACTERS = 500_000


def _serialized_character_count(value: object) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def _referenced_evidence_ids(value: object) -> set[str]:
    if isinstance(value, dict):
        own = set(value.get("evidence_ids", [])) if "evidence_ids" in value else set()
        return own | set().union(*(_referenced_evidence_ids(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(_referenced_evidence_ids(item) for item in value))
    return set()


class ContractModel(BaseModel):
    """Strict base model for portable TaskRelay contracts."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Evidence(ContractModel):
    """A caller-supplied evidence item that model conclusions may cite."""

    evidence_id: EvidenceId
    content: Annotated[str, Field(min_length=1, max_length=4_000)]
    source: Annotated[str, Field(min_length=1, max_length=500)]


class CreateCheckpointInput(ContractModel):
    """Material supplied to create a portable checkpoint."""

    goal: Annotated[str, Field(min_length=1, max_length=2_000)]
    session_material: Annotated[str, Field(min_length=1, max_length=12_000)]
    constraints: Annotated[list[ShortText], Field(max_length=30)] = Field(default_factory=list)
    decisions: Annotated[list[ShortText], Field(max_length=30)] = Field(default_factory=list)
    evidence: Annotated[list[Evidence], Field(min_length=1, max_length=50)]

    @model_validator(mode="after")
    def evidence_ids_are_unique(self) -> CreateCheckpointInput:
        evidence_ids = [item.evidence_id for item in self.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("evidence IDs must be unique")
        if (
            _serialized_character_count(self.model_dump(mode="json"))
            > MAX_CHECKPOINT_INPUT_CHARACTERS
        ):
            raise ValueError(f"total input exceeds {MAX_CHECKPOINT_INPUT_CHARACTERS} characters")
        return self


class GroundedStatement(ContractModel):
    """A conclusion backed by one or more caller evidence items."""

    text: ShortText
    evidence_ids: EvidenceIds


class ContextStatement(ContractModel):
    """Explicit context that may cite evidence but is not an inferred conclusion."""

    text: ShortText
    evidence_ids: Annotated[list[EvidenceId], Field(max_length=20)] = Field(default_factory=list)


class OpenQuestion(ContractModel):
    """An unresolved question carried into the next session."""

    question: ShortText
    evidence_ids: Annotated[list[EvidenceId], Field(max_length=20)] = Field(default_factory=list)


class NextStep(ContractModel):
    """A grounded action and its observable completion check."""

    action: ShortText
    verification: ShortText
    evidence_ids: EvidenceIds


class CheckpointDraft(ContractModel):
    """Hy3-authored checkpoint fields before local identity and evidence attachment."""

    goal: Annotated[str, Field(min_length=1, max_length=2_000)]
    confirmed_facts: Annotated[list[GroundedStatement], Field(max_length=50)]
    constraints: Annotated[list[GroundedStatement], Field(max_length=30)]
    decisions: Annotated[list[GroundedStatement], Field(max_length=30)]
    open_questions: Annotated[list[OpenQuestion], Field(max_length=30)]
    next_steps: Annotated[list[NextStep], Field(min_length=1, max_length=30)]

    @model_validator(mode="after")
    def total_size_is_bounded(self) -> CheckpointDraft:
        if (
            self.__class__ is CheckpointDraft
            and _serialized_character_count(self.model_dump(mode="json"))
            > MAX_CHECKPOINT_DRAFT_CHARACTERS
        ):
            raise ValueError(
                f"checkpoint draft exceeds {MAX_CHECKPOINT_DRAFT_CHARACTERS} characters"
            )
        return self


class Checkpoint(CheckpointDraft):
    """Portable, caller-owned TaskRelay checkpoint."""

    schema_version: Literal["1.0"]
    checkpoint_id: Annotated[str, Field(pattern=r"^cp_[0-9a-f]{16}$")]
    constraints: Annotated[list[ContextStatement], Field(max_length=30)]
    decisions: Annotated[list[ContextStatement], Field(max_length=30)]
    evidence: Annotated[list[Evidence], Field(min_length=1, max_length=70)]

    @model_validator(mode="after")
    def checkpoint_id_matches_content(self) -> Checkpoint:
        payload = self.model_dump(mode="json", exclude={"checkpoint_id"})
        if self.checkpoint_id != stable_content_id("cp", payload):
            raise ValueError("checkpoint_id does not match checkpoint content")
        evidence_ids = [item.evidence_id for item in self.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("checkpoint evidence IDs must be unique")
        missing_ids = _referenced_evidence_ids(payload) - set(evidence_ids)
        if missing_ids:
            raise ValueError(f"checkpoint references unknown evidence IDs: {sorted(missing_ids)}")
        if (
            _serialized_character_count(self.model_dump(mode="json"))
            > MAX_CHECKPOINT_ARTIFACT_CHARACTERS
        ):
            raise ValueError(f"checkpoint exceeds {MAX_CHECKPOINT_ARTIFACT_CHARACTERS} characters")
        return self


class AuditCheckpointInput(ContractModel):
    """A checkpoint plus optional new evidence to audit against it."""

    checkpoint: Checkpoint
    additional_evidence: Annotated[list[Evidence], Field(max_length=20)] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def evidence_ids_do_not_collide(self) -> AuditCheckpointInput:
        evidence_ids = [item.evidence_id for item in self.checkpoint.evidence]
        evidence_ids.extend(item.evidence_id for item in self.additional_evidence)
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("additional evidence IDs must not duplicate checkpoint evidence IDs")
        if _serialized_character_count(self.model_dump(mode="json")) > MAX_AUDIT_INPUT_CHARACTERS:
            raise ValueError(f"total audit input exceeds {MAX_AUDIT_INPUT_CHARACTERS} characters")
        return self


class AuditFindingDraft(ContractModel):
    """One Hy3-authored checkpoint defect before local identity is attached."""

    severity: Literal["critical", "high", "medium", "low"]
    category: Literal[
        "contradiction", "missing_constraint", "stale_assumption", "unsupported_claim"
    ]
    summary: ShortText
    evidence_ids: EvidenceIds
    recommendation: ShortText


class AuditFinding(AuditFindingDraft):
    """Stable audit finding tied to caller evidence."""

    finding_id: Annotated[str, Field(pattern=r"^finding_[0-9a-f]{16}$")]

    @model_validator(mode="after")
    def finding_id_matches_content(self) -> AuditFinding:
        payload = self.model_dump(mode="json", exclude={"finding_id"})
        if self.finding_id != stable_content_id("finding", payload):
            raise ValueError("finding_id does not match finding content")
        return self


class AuditDraft(ContractModel):
    """Hy3-authored audit result before local identifiers are attached."""

    overall_status: Literal["clean", "needs_attention", "blocked"]
    findings: Annotated[list[AuditFindingDraft], Field(max_length=50)]

    @model_validator(mode="after")
    def status_matches_findings(self) -> AuditDraft:
        if (self.overall_status == "clean") != (not self.findings):
            raise ValueError("overall_status must be clean exactly when findings is empty")
        serialized = [finding.model_dump_json() for finding in self.findings]
        if len(serialized) != len(set(serialized)):
            raise ValueError("audit findings must be unique")
        if _serialized_character_count(self.model_dump(mode="json")) > MAX_AUDIT_DRAFT_CHARACTERS:
            raise ValueError(f"audit draft exceeds {MAX_AUDIT_DRAFT_CHARACTERS} characters")
        return self


class AuditResult(ContractModel):
    """Portable checkpoint audit with grounded, severity-ranked findings."""

    schema_version: Literal["1.0"]
    checkpoint_id: Annotated[str, Field(pattern=r"^cp_[0-9a-f]{16}$")]
    overall_status: Literal["clean", "needs_attention", "blocked"]
    findings: Annotated[list[AuditFinding], Field(max_length=50)]
    evidence: Annotated[list[Evidence], Field(min_length=1, max_length=90)]

    @model_validator(mode="after")
    def status_and_findings_are_consistent(self) -> AuditResult:
        if (self.overall_status == "clean") != (not self.findings):
            raise ValueError("overall_status must be clean exactly when findings is empty")
        finding_ids = [finding.finding_id for finding in self.findings]
        if len(finding_ids) != len(set(finding_ids)):
            raise ValueError("finding IDs must be unique")
        evidence_ids = [item.evidence_id for item in self.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("audit evidence IDs must be unique")
        missing_ids = _referenced_evidence_ids(self.model_dump(mode="json")) - set(evidence_ids)
        if missing_ids:
            raise ValueError("audit references unknown evidence IDs")
        if (
            _serialized_character_count(self.model_dump(mode="json"))
            > MAX_AUDIT_ARTIFACT_CHARACTERS
        ):
            raise ValueError(f"audit exceeds {MAX_AUDIT_ARTIFACT_CHARACTERS} characters")
        return self


class CreateResumeBriefInput(ContractModel):
    """Checkpoint, audit, and optional new context used to plan continuation."""

    checkpoint: Checkpoint
    audit: AuditResult
    additional_evidence: Annotated[list[Evidence], Field(max_length=20)] = Field(
        default_factory=list
    )
    continuation_context: Annotated[str, Field(max_length=4_000)] = ""

    @model_validator(mode="after")
    def related_artifacts_are_consistent(self) -> CreateResumeBriefInput:
        if self.audit.checkpoint_id != self.checkpoint.checkpoint_id:
            raise ValueError("audit.checkpoint_id must match checkpoint.checkpoint_id")
        audit_evidence = {item.evidence_id: item for item in self.audit.evidence}
        for item in self.checkpoint.evidence:
            if audit_evidence.get(item.evidence_id) != item:
                raise ValueError("audit evidence must include the unchanged checkpoint evidence")
        additional_ids = [item.evidence_id for item in self.additional_evidence]
        if len(additional_ids) != len(set(additional_ids)) or set(additional_ids) & set(
            audit_evidence
        ):
            raise ValueError("resume additional evidence IDs must be new and unique")
        if _serialized_character_count(self.model_dump(mode="json")) > MAX_RESUME_INPUT_CHARACTERS:
            raise ValueError(f"total resume input exceeds {MAX_RESUME_INPUT_CHARACTERS} characters")
        return self


class PriorityStep(ContractModel):
    """A continuation action ordered by urgency and paired with a validation gate."""

    priority: Annotated[int, Field(ge=1, le=20)]
    action: ShortText
    validation: ShortText
    evidence_ids: EvidenceIds


class ResumeDraft(ContractModel):
    """Hy3-authored continuation brief before local identity is attached."""

    concise_context: Annotated[list[GroundedStatement], Field(min_length=1, max_length=10)]
    next_steps: Annotated[list[PriorityStep], Field(min_length=1, max_length=20)]
    blockers: Annotated[list[GroundedStatement], Field(max_length=20)]
    do_not: Annotated[list[GroundedStatement], Field(max_length=20)]

    @model_validator(mode="after")
    def priorities_are_unique(self) -> ResumeDraft:
        priorities = [step.priority for step in self.next_steps]
        if len(priorities) != len(set(priorities)):
            raise ValueError("next step priorities must be unique")
        if (
            self.__class__ is ResumeDraft
            and _serialized_character_count(self.model_dump(mode="json"))
            > MAX_RESUME_DRAFT_CHARACTERS
        ):
            raise ValueError(f"resume draft exceeds {MAX_RESUME_DRAFT_CHARACTERS} characters")
        return self


class ResumeBrief(ResumeDraft):
    """Portable, ordered continuation brief for another session or client."""

    schema_version: Literal["1.0"]
    checkpoint_id: Annotated[str, Field(pattern=r"^cp_[0-9a-f]{16}$")]
    resume_id: Annotated[str, Field(pattern=r"^resume_[0-9a-f]{16}$")]
    evidence: Annotated[list[Evidence], Field(min_length=1, max_length=110)]

    @model_validator(mode="after")
    def resume_id_matches_content(self) -> ResumeBrief:
        payload = self.model_dump(mode="json", exclude={"resume_id"})
        if self.resume_id != stable_content_id("resume", payload):
            raise ValueError("resume_id does not match resume brief content")
        evidence_ids = [item.evidence_id for item in self.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("resume evidence IDs must be unique")
        missing_ids = _referenced_evidence_ids(payload) - set(evidence_ids)
        if missing_ids:
            raise ValueError("resume brief references unknown evidence IDs")
        if (
            _serialized_character_count(self.model_dump(mode="json"))
            > MAX_RESUME_ARTIFACT_CHARACTERS
        ):
            raise ValueError(f"resume brief exceeds {MAX_RESUME_ARTIFACT_CHARACTERS} characters")
        return self
