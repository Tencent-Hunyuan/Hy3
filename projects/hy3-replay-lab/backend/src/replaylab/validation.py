from __future__ import annotations

from replaylab.schemas import AnalysisDraft, ReplayPlan, TaskSpec, ValidationGate


class OutputValidationError(ValueError):
    """Raised when model-authored output fails deterministic safety rules."""


def validate_analysis_draft(task: TaskSpec, draft: AnalysisDraft) -> None:
    criterion_ids = [item.criterion_id for item in task.criteria]
    step_ids = [item.step_id for item in task.trace]
    evidence_ids = [item.evidence_id for item in task.evidence]
    known_criteria = set(criterion_ids)
    known_steps = set(step_ids)
    known_evidence = set(evidence_ids)

    coverage_ids = [item.criterion_id for item in draft.coverage]
    if coverage_ids != criterion_ids:
        raise OutputValidationError("coverage must contain every criterion once in input order")

    for item in draft.coverage:
        _require_refs(item.supporting_step_ids, known_steps, "coverage step")
        _require_refs(item.evidence_ids, known_evidence, "coverage evidence")

    finding = draft.finding
    if finding.category == "no_divergence":
        if finding.first_divergence_step_id is not None or finding.impact_step_ids:
            raise OutputValidationError("a no-divergence finding cannot identify divergent steps")
    elif finding.first_divergence_step_id is None:
        raise OutputValidationError("a divergence finding must identify the first divergent step")
    if finding.first_divergence_step_id is not None:
        _require_refs([finding.first_divergence_step_id], known_steps, "finding step")
    _require_refs(finding.impact_step_ids, known_steps, "finding impact step")
    _require_refs(finding.evidence_ids, known_evidence, "finding evidence")
    if finding.first_divergence_step_id is not None:
        divergence_index = step_ids.index(finding.first_divergence_step_id)
        step_indexes = {step_id: index for index, step_id in enumerate(step_ids)}
        evidence_indexes = {
            item.evidence_id: step_indexes[item.step_id] for item in task.evidence
        }
        if any(evidence_indexes[item] > divergence_index for item in finding.evidence_ids):
            raise OutputValidationError(
                "finding evidence must exist at or before the first divergent step"
            )
        if any(step_indexes[item] <= divergence_index for item in finding.impact_step_ids):
            raise OutputValidationError(
                "finding impact steps must follow the first divergent step"
            )
        impact_steps = set(finding.impact_step_ids)
        ordered_impacts = [
            item for item in step_ids[divergence_index + 1 :] if item in impact_steps
        ]
        if finding.impact_step_ids != ordered_impacts:
            raise OutputValidationError("finding impact steps must follow timeline order")

    _validate_replay_plan(
        draft.replay_plan,
        criterion_ids=known_criteria,
        step_ids=step_ids,
        evidence_ids=known_evidence,
        first_divergence_step_id=finding.first_divergence_step_id,
    )


def _validate_replay_plan(
    plan: ReplayPlan,
    *,
    criterion_ids: set[str],
    step_ids: list[str],
    evidence_ids: set[str],
    first_divergence_step_id: str | None,
) -> None:
    known_steps = set(step_ids)
    _require_refs(plan.preserved_step_ids, known_steps, "preserved step")
    _require_refs(plan.rerun_step_ids, known_steps, "rerun step")

    if first_divergence_step_id is None:
        if plan.rerun_from_step_id is not None or plan.rerun_step_ids or plan.actions:
            raise OutputValidationError("a no-divergence replay plan must not rerun steps")
        if plan.preserved_step_ids != step_ids:
            raise OutputValidationError(
                "a no-divergence replay plan must preserve the complete trace"
            )
    else:
        if plan.rerun_from_step_id != first_divergence_step_id:
            raise OutputValidationError("replay must begin at the first divergent step")
        if not plan.rerun_step_ids or plan.rerun_step_ids[0] != first_divergence_step_id:
            raise OutputValidationError("rerun steps must begin at the first divergent step")
        if not plan.actions:
            raise OutputValidationError("a divergence replay plan must contain an action")
        divergence_index = step_ids.index(first_divergence_step_id)
        if plan.preserved_step_ids != step_ids[:divergence_index]:
            raise OutputValidationError(
                "preserved steps must be the exact prefix before divergence"
            )
        expected_order = [item for item in step_ids if item in set(plan.rerun_step_ids)]
        if plan.rerun_step_ids != expected_order:
            raise OutputValidationError("rerun steps must follow timeline order")

    action_orders = [item.order for item in plan.actions]
    if action_orders != list(range(1, len(action_orders) + 1)):
        raise OutputValidationError("replay actions must be numbered consecutively from one")

    for action in plan.actions:
        _require_refs(action.evidence_ids, evidence_ids, "action evidence")
        _validate_gate(action.validation_gate, criterion_ids, evidence_ids)
    for gate in plan.stop_conditions:
        _validate_gate(gate, criterion_ids, evidence_ids)
    for prohibited in plan.prohibited_actions:
        _require_refs(prohibited.evidence_ids, evidence_ids, "prohibited-action evidence")


def _validate_gate(gate: ValidationGate, criterion_ids: set[str], evidence_ids: set[str]) -> None:
    _require_refs(gate.criterion_ids, criterion_ids, "validation-gate criterion")
    _require_refs(gate.evidence_ids, evidence_ids, "validation-gate evidence")


def _require_refs(values: list[str], known: set[str], label: str) -> None:
    if len(values) != len(set(values)):
        raise OutputValidationError(f"{label} references must be unique")
    if set(values) - known:
        raise OutputValidationError(f"{label} references contain unknown IDs")
