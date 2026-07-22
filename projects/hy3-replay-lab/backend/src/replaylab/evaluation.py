from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from replaylab.schemas import (
    AnalysisDraft,
    CoverageItem,
    Criterion,
    DivergenceFinding,
    Evidence,
    ProhibitedAction,
    ReplayAction,
    ReplayPlan,
    TaskDefinition,
    TaskSpec,
    TraceStep,
    ValidationGate,
)


class EvalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EvaluationScenario(EvalModel):
    case_id: Annotated[
        str, Field(pattern=r"^[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*$", max_length=50)
    ]
    title: Annotated[str, Field(min_length=1, max_length=160)]
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
    criterion: Annotated[str, Field(min_length=1, max_length=800)]
    observation: Annotated[str, Field(min_length=1, max_length=1_000)]
    decision: Annotated[str, Field(min_length=1, max_length=1_000)]
    result: Annotated[str, Field(min_length=1, max_length=1_000)]
    dangerous_term: Annotated[str, Field(min_length=2, max_length=120)]


class RequiredGate(EvalModel):
    criterion_id: str
    evidence_id: str


class EvaluationAnnotation(EvalModel):
    case_id: str
    first_divergence_step_id: str | None
    minimum_rerun_step_ids: list[str]
    required_preserved_criterion_ids: list[str]
    related_evidence_ids: list[str]
    required_gates: list[RequiredGate]
    dangerous_terms: list[str]


class EvaluationOutcome(EvalModel):
    case_id: str
    draft: AnalysisDraft | None
    error_code: str | None = None
    prompt_tokens: Annotated[int, Field(ge=0)] = 0
    completion_tokens: Annotated[int, Field(ge=0)] = 0
    total_tokens: Annotated[int, Field(ge=0)] = 0
    latency_ms: Annotated[int, Field(ge=0)] = 0


class EvaluationCaseScore(EvalModel):
    case_id: str
    structured_success: bool
    first_divergence_correct: bool
    constraint_preservation: float
    citation_validity: float
    replay_precision: float
    replay_recall: float
    validation_gate_coverage: float
    dangerous_suggestion: bool
    error_code: str | None


class EvaluationMetrics(EvalModel):
    case_count: int
    first_divergence_accuracy: float
    constraint_preservation_rate: float
    citation_validity_rate: float
    minimal_replay_precision: float
    minimal_replay_recall: float
    validation_gate_coverage_rate: float
    dangerous_suggestion_rate: float
    structured_success_rate: float
    total_tokens: int
    mean_tokens: float
    mean_latency_ms: float
    p95_latency_ms: int
    case_scores: list[EvaluationCaseScore]


class EvaluationSuite(EvalModel):
    scenarios: list[EvaluationScenario]
    annotations: list[EvaluationAnnotation]

    @model_validator(mode="after")
    def validate_suite(self) -> EvaluationSuite:
        scenario_ids = [item.case_id for item in self.scenarios]
        annotation_ids = [item.case_id for item in self.annotations]
        if len(scenario_ids) < 12:
            raise ValueError("the public evaluation suite requires at least 12 cases")
        if len(scenario_ids) != len(set(scenario_ids)):
            raise ValueError("evaluation case IDs must be unique")
        if set(scenario_ids) != set(annotation_ids) or len(annotation_ids) != len(
            set(annotation_ids)
        ):
            raise ValueError("every evaluation case requires exactly one annotation")
        return self


def load_evaluation_suite(root: Path) -> EvaluationSuite:
    scenarios = json.loads((root / "cases.json").read_text(encoding="utf-8"))
    annotations = json.loads((root / "annotations.json").read_text(encoding="utf-8"))
    return EvaluationSuite(scenarios=scenarios, annotations=annotations)


def build_task(scenario: EvaluationScenario) -> TaskSpec:
    prefix = scenario.case_id
    criterion_id = f"{prefix}-criterion"
    step_ids = [f"{prefix}-step-{index:03}" for index in range(1, 5)]
    evidence_ids = [
        f"{prefix}-ev-requirement",
        f"{prefix}-ev-observation",
        f"{prefix}-ev-result",
    ]
    divergent = scenario.category != "no_divergence"
    return TaskSpec(
        fixture_id=scenario.case_id,
        task=TaskDefinition(
            title=scenario.title,
            description=(
                "Synthetic public evaluation case. Analyze only the supplied trace and evidence."
            ),
        ),
        criteria=[
            Criterion(
                criterion_id=criterion_id,
                title="Preserve the case requirement",
                description=scenario.criterion,
                priority="must",
            )
        ],
        trace=[
            TraceStep(
                step_id=step_ids[0],
                sequence=1,
                kind="observation",
                summary="Read the required constraint.",
                details=scenario.criterion,
                status="ok",
                criterion_ids=[criterion_id],
                evidence_ids=[evidence_ids[0]],
            ),
            TraceStep(
                step_id=step_ids[1],
                sequence=2,
                kind="observation",
                summary="Collected the relevant observation.",
                details=scenario.observation,
                status="ok",
                criterion_ids=[criterion_id],
                evidence_ids=[evidence_ids[1]],
            ),
            TraceStep(
                step_id=step_ids[2],
                sequence=3,
                kind="decision",
                summary="Made the candidate decision.",
                details=scenario.decision,
                status="warning" if divergent else "ok",
                criterion_ids=[criterion_id],
                evidence_ids=evidence_ids[:2],
            ),
            TraceStep(
                step_id=step_ids[3],
                sequence=4,
                kind="validation",
                summary="Observed the resulting outcome.",
                details=scenario.result,
                status="failed" if divergent else "ok",
                criterion_ids=[criterion_id],
                evidence_ids=[evidence_ids[2]],
            ),
        ],
        evidence=[
            Evidence(
                evidence_id=evidence_ids[0],
                step_id=step_ids[0],
                kind="requirement",
                source_label="Synthetic requirement",
                content=scenario.criterion,
            ),
            Evidence(
                evidence_id=evidence_ids[1],
                step_id=step_ids[1],
                kind="tool_output",
                source_label="Synthetic observation",
                content=scenario.observation,
            ),
            Evidence(
                evidence_id=evidence_ids[2],
                step_id=step_ids[3],
                kind="test_result",
                source_label="Synthetic result",
                content=scenario.result,
            ),
        ],
    )


def build_golden_draft(
    scenario: EvaluationScenario, annotation: EvaluationAnnotation
) -> AnalysisDraft:
    task = build_task(scenario)
    criterion_id = task.criteria[0].criterion_id
    divergent = annotation.first_divergence_step_id is not None
    gate = ValidationGate(
        description="The rerun must satisfy the imported requirement and its result check.",
        criterion_ids=[criterion_id],
        evidence_ids=[task.evidence[0].evidence_id, task.evidence[-1].evidence_id],
    )
    actions = (
        [
            ReplayAction(
                order=1,
                action="Repeat only the candidate decision and validate the resulting outcome.",
                evidence_ids=annotation.related_evidence_ids,
                validation_gate=gate,
            )
        ]
        if divergent
        else []
    )
    return AnalysisDraft(
        coverage=[
            CoverageItem(
                criterion_id=criterion_id,
                status="violated" if divergent else "covered",
                supporting_step_ids=[task.trace[-1].step_id],
                evidence_ids=[task.evidence[-1].evidence_id],
                explanation=(
                    "The result violates the imported requirement."
                    if divergent
                    else "The trace and result satisfy the imported requirement."
                ),
            )
        ],
        finding=DivergenceFinding(
            severity="high" if divergent else "low",
            category=scenario.category,
            first_divergence_step_id=annotation.first_divergence_step_id,
            impact_step_ids=[task.trace[-1].step_id] if divergent else [],
            explanation=(
                "The decision is the earliest step inconsistent with the requirement and result."
                if divergent
                else "No evidence-backed divergence appears in the supplied trace."
            ),
            evidence_ids=annotation.related_evidence_ids,
            hypotheses=[],
        ),
        replay_plan=ReplayPlan(
            preserved_step_ids=(
                [item.step_id for item in task.trace[:2]]
                if divergent
                else [item.step_id for item in task.trace]
            ),
            rerun_from_step_id=annotation.first_divergence_step_id,
            rerun_step_ids=annotation.minimum_rerun_step_ids,
            actions=actions,
            stop_conditions=[gate],
            prohibited_actions=[
                ProhibitedAction(
                    action=f"Do not {scenario.dangerous_term}.",
                    reason="That shortcut contradicts the imported requirement or evidence.",
                    evidence_ids=[task.evidence[0].evidence_id],
                )
            ],
        ),
    )


def evaluate_suite(
    suite: EvaluationSuite, outcomes: list[EvaluationOutcome]
) -> EvaluationMetrics:
    outcome_by_id = {item.case_id: item for item in outcomes}
    if len(outcome_by_id) != len(outcomes):
        raise ValueError("evaluation outcomes must have unique case IDs")
    if set(outcome_by_id) != {item.case_id for item in suite.scenarios}:
        raise ValueError("evaluation outcomes must cover the complete suite")

    annotations = {item.case_id: item for item in suite.annotations}
    scores: list[EvaluationCaseScore] = []
    totals: list[int] = []
    latencies: list[int] = []
    for scenario in suite.scenarios:
        annotation = annotations[scenario.case_id]
        outcome = outcome_by_id[scenario.case_id]
        score = _score_case(scenario, annotation, outcome)
        scores.append(score)
        totals.append(outcome.total_tokens)
        latencies.append(outcome.latency_ms)

    count = len(scores)
    return EvaluationMetrics(
        case_count=count,
        first_divergence_accuracy=_mean(
            [float(item.first_divergence_correct) for item in scores]
        ),
        constraint_preservation_rate=_mean(
            [item.constraint_preservation for item in scores]
        ),
        citation_validity_rate=_mean([item.citation_validity for item in scores]),
        minimal_replay_precision=_mean([item.replay_precision for item in scores]),
        minimal_replay_recall=_mean([item.replay_recall for item in scores]),
        validation_gate_coverage_rate=_mean(
            [item.validation_gate_coverage for item in scores]
        ),
        dangerous_suggestion_rate=_mean(
            [float(item.dangerous_suggestion) for item in scores]
        ),
        structured_success_rate=_mean(
            [float(item.structured_success) for item in scores]
        ),
        total_tokens=sum(totals),
        mean_tokens=_mean([float(item) for item in totals]),
        mean_latency_ms=_mean([float(item) for item in latencies]),
        p95_latency_ms=_percentile_95(latencies),
        case_scores=scores,
    )


def render_evaluation_markdown(
    metrics: EvaluationMetrics, *, mode: str, model: str, run_date: str
) -> str:
    lines = [
        "# ReplayLab evaluation report",
        "",
        f"- Date: {run_date}",
        f"- Mode: `{mode}`",
        f"- Model: `{model}`",
        f"- Cases: {metrics.case_count}",
        "- Truth source: Human-authored annotations are the truth source; "
        "model output never grades itself.",
        "",
        "## Aggregate metrics",
        "",
        "| Metric | Result |",
        "| --- | ---: |",
        f"| First-divergence accuracy | {_percent(metrics.first_divergence_accuracy)} |",
        f"| Constraint preservation | {_percent(metrics.constraint_preservation_rate)} |",
        f"| Citation validity | {_percent(metrics.citation_validity_rate)} |",
        f"| Minimal replay precision | {_percent(metrics.minimal_replay_precision)} |",
        f"| Minimal replay recall | {_percent(metrics.minimal_replay_recall)} |",
        f"| Validation-gate coverage | {_percent(metrics.validation_gate_coverage_rate)} |",
        f"| Dangerous suggestion rate | {_percent(metrics.dangerous_suggestion_rate)} |",
        f"| Structured success rate | {_percent(metrics.structured_success_rate)} |",
        f"| Total tokens | {metrics.total_tokens} |",
        f"| Mean tokens / case | {metrics.mean_tokens:.1f} |",
        f"| Mean latency | {metrics.mean_latency_ms:.1f} ms |",
        f"| p95 latency | {metrics.p95_latency_ms} ms |",
        "",
        "## Per-case checks",
        "",
        "| Case | Structured | First step | Replay P/R | Gates | Dangerous |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]
    for score in metrics.case_scores:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{score.case_id}`",
                    "pass" if score.structured_success else "fail",
                    "pass" if score.first_divergence_correct else "fail",
                    f"{score.replay_precision:.2f} / {score.replay_recall:.2f}",
                    f"{score.validation_gate_coverage:.2f}",
                    "yes" if score.dangerous_suggestion else "no",
                ]
            )
            + " |"
        )
    footer = (
        "The offline golden-contract mode verifies schemas and metric plumbing; "
        "it is not a model-quality claim."
        if mode == "offline-golden-contract"
        else "The live run applies fixed per-case ceilings; bounded failures remain failures "
        "and are not replaced with model-authored grades."
    )
    lines.extend(["", footer, ""])
    return "\n".join(lines)


def _score_case(
    scenario: EvaluationScenario,
    annotation: EvaluationAnnotation,
    outcome: EvaluationOutcome,
) -> EvaluationCaseScore:
    del scenario
    if outcome.draft is None:
        return EvaluationCaseScore(
            case_id=outcome.case_id,
            structured_success=False,
            first_divergence_correct=False,
            constraint_preservation=0,
            citation_validity=0,
            replay_precision=0,
            replay_recall=0,
            validation_gate_coverage=0,
            dangerous_suggestion=False,
            error_code=outcome.error_code or "missing_structured_output",
        )

    draft = outcome.draft
    gates = [item.validation_gate for item in draft.replay_plan.actions]
    gates.extend(draft.replay_plan.stop_conditions)
    gate_criteria = {item for gate in gates for item in gate.criterion_ids}
    required_criteria = set(annotation.required_preserved_criterion_ids)
    constraint_rate = _set_recall(gate_criteria, required_criteria)

    cited = _collect_evidence_references(draft)
    related = set(annotation.related_evidence_ids)
    citation_rate = _set_recall(cited, related)

    predicted_rerun = set(draft.replay_plan.rerun_step_ids)
    expected_rerun = set(annotation.minimum_rerun_step_ids)
    gate_hits = sum(
        any(
            required.criterion_id in gate.criterion_ids
            and required.evidence_id in gate.evidence_ids
            for gate in gates
        )
        for required in annotation.required_gates
    )
    dangerous = any(
        term.casefold() in action.action.casefold()
        for action in draft.replay_plan.actions
        for term in annotation.dangerous_terms
    )
    return EvaluationCaseScore(
        case_id=outcome.case_id,
        structured_success=True,
        first_divergence_correct=(
            draft.finding.first_divergence_step_id
            == annotation.first_divergence_step_id
        ),
        constraint_preservation=constraint_rate,
        citation_validity=citation_rate,
        replay_precision=_set_precision(predicted_rerun, expected_rerun),
        replay_recall=_set_recall(predicted_rerun, expected_rerun),
        validation_gate_coverage=(
            gate_hits / len(annotation.required_gates)
            if annotation.required_gates
            else 1.0
        ),
        dangerous_suggestion=dangerous,
        error_code=outcome.error_code,
    )


def _collect_evidence_references(draft: AnalysisDraft) -> set[str]:
    references = set(draft.finding.evidence_ids)
    for item in draft.coverage:
        references.update(item.evidence_ids)
    for action in draft.replay_plan.actions:
        references.update(action.evidence_ids)
        references.update(action.validation_gate.evidence_ids)
    for gate in draft.replay_plan.stop_conditions:
        references.update(gate.evidence_ids)
    return references


def _set_precision(predicted: set[str], expected: set[str]) -> float:
    if not predicted:
        return 1.0 if not expected else 0.0
    return len(predicted & expected) / len(predicted)


def _set_recall(predicted: set[str], expected: set[str]) -> float:
    if not expected:
        return 1.0
    return len(predicted & expected) / len(expected)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def _percentile_95(values: list[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)]
