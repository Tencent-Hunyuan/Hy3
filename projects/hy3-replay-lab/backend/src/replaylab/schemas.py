from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Identifier = Annotated[
    str,
    Field(
        min_length=3,
        max_length=80,
        pattern=r"^[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*$",
    ),
]
ShortText = Annotated[str, Field(min_length=1, max_length=400)]
LongText = Annotated[str, Field(min_length=1, max_length=5_000)]
MAX_TOTAL_INPUT_BYTES = 256_000


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)


class TaskDefinition(StrictModel):
    title: Annotated[str, Field(min_length=1, max_length=160)]
    description: LongText


class Criterion(StrictModel):
    criterion_id: Identifier
    title: Annotated[str, Field(min_length=1, max_length=160)]
    description: Annotated[str, Field(min_length=1, max_length=1_000)]
    priority: Literal["must", "should", "could"] = "must"


class TraceStep(StrictModel):
    step_id: Identifier
    sequence: Annotated[int, Field(ge=1, le=1_000)]
    kind: Literal[
        "observation",
        "decision",
        "tool_call",
        "tool_result",
        "action",
        "validation",
        "claim",
    ]
    summary: ShortText
    details: LongText
    status: Literal["ok", "warning", "failed", "unknown"] = "unknown"
    criterion_ids: Annotated[list[Identifier], Field(max_length=50)] = Field(default_factory=list)
    evidence_ids: Annotated[list[Identifier], Field(max_length=50)] = Field(default_factory=list)


class Evidence(StrictModel):
    evidence_id: Identifier
    step_id: Identifier
    step_sequence: Annotated[int | None, Field(ge=1, le=1_000, exclude=True)] = None
    kind: Literal[
        "requirement",
        "tool_output",
        "test_result",
        "source_excerpt",
        "artifact",
        "note",
    ]
    source_label: Annotated[str, Field(min_length=1, max_length=200)]
    content: LongText


class TaskSpec(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    fixture_id: Identifier | None = None
    task: TaskDefinition
    criteria: Annotated[list[Criterion], Field(min_length=1, max_length=50)]
    trace: Annotated[list[TraceStep], Field(min_length=1, max_length=200)]
    evidence: Annotated[list[Evidence], Field(min_length=1, max_length=200)]

    @model_validator(mode="before")
    @classmethod
    def generate_missing_identifiers(cls, value: object) -> object:
        if not isinstance(value, Mapping):
            return value
        payload = copy.deepcopy(dict(value))
        criteria = payload.get("criteria")
        trace = payload.get("trace")
        evidence = payload.get("evidence")
        if (
            not isinstance(criteria, list)
            or not isinstance(trace, list)
            or not isinstance(evidence, list)
        ):
            return payload

        for index, item in enumerate(criteria, start=1):
            if isinstance(item, dict) and not item.get("criterion_id"):
                item["criterion_id"] = _stable_import_id("criterion", index, item)

        sequence_to_step_id: dict[int, str] = {}
        for index, item in enumerate(trace, start=1):
            if not isinstance(item, dict):
                continue
            sequence = item.get("sequence")
            ordinal = sequence if isinstance(sequence, int) else index
            if not item.get("step_id"):
                item["step_id"] = _stable_import_id("step", ordinal, item)
            if isinstance(sequence, int) and isinstance(item["step_id"], str):
                sequence_to_step_id[sequence] = item["step_id"]

        for index, item in enumerate(evidence, start=1):
            if not isinstance(item, dict):
                continue
            if not item.get("evidence_id"):
                item["evidence_id"] = _stable_import_id("evidence", index, item)
            source_sequence = item.pop("step_sequence", None)
            if not item.get("step_id"):
                if (
                    not isinstance(source_sequence, int)
                    or source_sequence not in sequence_to_step_id
                ):
                    raise ValueError("evidence without step_id requires a known step_sequence")
                item["step_id"] = sequence_to_step_id[source_sequence]
            elif source_sequence is not None:
                expected_step_id = sequence_to_step_id.get(source_sequence)
                if expected_step_id is None or item["step_id"] != expected_step_id:
                    raise ValueError(
                        "evidence step_id and step_sequence must identify the same step"
                    )
        return payload

    @model_validator(mode="after")
    def validate_input_references(self) -> TaskSpec:
        criterion_ids = [item.criterion_id for item in self.criteria]
        step_ids = [item.step_id for item in self.trace]
        evidence_ids = [item.evidence_id for item in self.evidence]

        _require_unique("criterion IDs", criterion_ids)
        _require_unique("step IDs", step_ids)
        _require_unique("evidence IDs", evidence_ids)

        sequences = [item.sequence for item in self.trace]
        if sequences != sorted(sequences) or len(sequences) != len(set(sequences)):
            raise ValueError("trace steps must be in strictly increasing sequence order")

        known_criteria = set(criterion_ids)
        known_steps = set(step_ids)
        known_evidence = set(evidence_ids)
        for step in self.trace:
            _require_subset(
                f"criterion references on {step.step_id}", step.criterion_ids, known_criteria
            )
            _require_subset(
                f"evidence references on {step.step_id}", step.evidence_ids, known_evidence
            )
        for item in self.evidence:
            if item.step_id not in known_steps:
                raise ValueError(f"evidence {item.evidence_id} references an unknown step")
        total_bytes = len(self.model_dump_json(exclude_none=True).encode("utf-8"))
        if total_bytes > MAX_TOTAL_INPUT_BYTES:
            raise ValueError("total input exceeds the 256000-byte budget")
        return self


class CoverageItem(StrictModel):
    criterion_id: Identifier
    status: Literal["covered", "violated", "unknown"]
    supporting_step_ids: Annotated[list[Identifier], Field(max_length=200)]
    evidence_ids: Annotated[list[Identifier], Field(min_length=1, max_length=200)]
    explanation: Annotated[str, Field(min_length=1, max_length=1_000)]


class DivergenceFinding(StrictModel):
    severity: Literal["low", "medium", "high", "critical"]
    category: Literal[
        "constraint_omission",
        "repeated_loop",
        "tool_misuse",
        "evidence_gap",
        "citation_error",
        "unsafe_action",
        "resource_limit",
        "no_divergence",
        "other",
    ]
    first_divergence_step_id: Identifier | None
    impact_step_ids: Annotated[list[Identifier], Field(max_length=200)]
    explanation: Annotated[str, Field(min_length=1, max_length=1_500)]
    evidence_ids: Annotated[list[Identifier], Field(min_length=1, max_length=200)]
    hypotheses: Annotated[list[ShortText], Field(max_length=20)] = Field(default_factory=list)


class ValidationGate(StrictModel):
    description: Annotated[str, Field(min_length=1, max_length=800)]
    criterion_ids: Annotated[list[Identifier], Field(min_length=1, max_length=50)]
    evidence_ids: Annotated[list[Identifier], Field(min_length=1, max_length=200)]


class ReplayAction(StrictModel):
    order: Annotated[int, Field(ge=1, le=200)]
    action: Annotated[str, Field(min_length=1, max_length=1_000)]
    evidence_ids: Annotated[list[Identifier], Field(min_length=1, max_length=200)]
    validation_gate: ValidationGate


class ProhibitedAction(StrictModel):
    action: Annotated[str, Field(min_length=1, max_length=800)]
    reason: Annotated[str, Field(min_length=1, max_length=1_000)]
    evidence_ids: Annotated[list[Identifier], Field(min_length=1, max_length=200)]


class ReplayPlan(StrictModel):
    preserved_step_ids: Annotated[list[Identifier], Field(max_length=200)]
    rerun_from_step_id: Identifier | None
    rerun_step_ids: Annotated[list[Identifier], Field(max_length=200)]
    actions: Annotated[list[ReplayAction], Field(max_length=50)]
    stop_conditions: Annotated[list[ValidationGate], Field(min_length=1, max_length=20)]
    prohibited_actions: Annotated[list[ProhibitedAction], Field(min_length=1, max_length=20)]


class AnalysisDraft(StrictModel):
    coverage: Annotated[list[CoverageItem], Field(min_length=1, max_length=50)]
    finding: DivergenceFinding
    replay_plan: ReplayPlan


class AnalysisMetadata(StrictModel):
    provider: Annotated[str, Field(min_length=1, max_length=80)]
    model: Annotated[str, Field(min_length=1, max_length=80)]
    mode: Literal["fake", "live"]
    latency_ms: Annotated[int, Field(ge=0)] | None = None
    prompt_tokens: Annotated[int, Field(ge=0)] | None = None
    completion_tokens: Annotated[int, Field(ge=0)] | None = None
    total_tokens: Annotated[int, Field(ge=0)] | None = None
    request_attempts: Annotated[int, Field(ge=1, le=10)] | None = None


class ReplayReport(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    report_id: Identifier
    fixture_id: Identifier | None
    task: TaskDefinition
    criteria: list[Criterion]
    timeline: list[TraceStep]
    evidence: list[Evidence]
    coverage: list[CoverageItem]
    finding: DivergenceFinding
    replay_plan: ReplayPlan
    metadata: AnalysisMetadata


def _require_unique(label: str, values: list[str]) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")


def _require_subset(label: str, values: list[str], known: set[str]) -> None:
    unknown = set(values) - known
    if unknown:
        raise ValueError(f"{label} contain unknown IDs")


def _stable_import_id(prefix: str, ordinal: int, payload: Mapping[str, object]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()[:10]
    return f"{prefix}_{ordinal:03}_{digest}"
