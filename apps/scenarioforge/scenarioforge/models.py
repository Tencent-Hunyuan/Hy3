"""Input normalization and output contract checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class ContractError(ValueError):
    """Raised when input or Hy3 output violates the public contract."""


def _clean_text(value: Any, field: str, *, limit: int, minimum: int = 1) -> str:
    if not isinstance(value, str):
        raise ContractError(f"{field} must be a string")
    cleaned = " ".join(value.split())
    if len(cleaned) < minimum:
        raise ContractError(f"{field} is too short")
    if len(cleaned) > limit:
        raise ContractError(f"{field} exceeds {limit} characters")
    return cleaned


@dataclass(frozen=True)
class RehearsalRequest:
    title: str
    goal: str
    plan: str
    constraints: tuple[str, ...]
    example_id: str | None = None

    @classmethod
    def from_json(cls, payload: Any) -> RehearsalRequest:
        if not isinstance(payload, dict):
            raise ContractError("request body must be a JSON object")
        raw_constraints = payload.get("constraints")
        if not isinstance(raw_constraints, list) or not raw_constraints:
            raise ContractError("constraints must be a non-empty array")
        if len(raw_constraints) > 12:
            raise ContractError("constraints may contain at most 12 items")
        constraints = tuple(
            _clean_text(item, f"constraints[{index}]", limit=240)
            for index, item in enumerate(raw_constraints)
        )
        example_id = payload.get("example_id", payload.get("id"))
        if example_id is not None and not isinstance(example_id, str):
            raise ContractError("example_id must be a string")
        return cls(
            title=_clean_text(payload.get("title"), "title", limit=120, minimum=3),
            goal=_clean_text(payload.get("goal"), "goal", limit=800, minimum=10),
            plan=_clean_text(payload.get("plan"), "plan", limit=12_000, minimum=30),
            constraints=constraints,
            example_id=example_id,
        )

    def as_prompt_payload(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "goal": self.goal,
            "plan": self.plan,
            "constraints": list(self.constraints),
        }


def validate_analysis(value: Any) -> dict[str, Any]:
    root = _object(value, "analysis")
    brief = _object(root.get("brief"), "analysis.brief")
    normalized = {
        "brief": {
            "objective": _clean_text(
                brief.get("objective"), "analysis.brief.objective", limit=600
            ),
            "non_negotiables": _string_list(
                brief.get("non_negotiables"),
                "analysis.brief.non_negotiables",
                minimum=2,
                maximum=8,
            ),
            "assumptions": _string_list(
                brief.get("assumptions"),
                "analysis.brief.assumptions",
                minimum=1,
                maximum=8,
            ),
        },
        "perspectives": _object_list(
            root.get("perspectives"),
            "analysis.perspectives",
            fields=("name", "concern", "evidence_from_plan", "severity"),
            minimum=3,
            maximum=5,
        ),
        "scenarios": _object_list(
            root.get("scenarios"),
            "analysis.scenarios",
            fields=("title", "trigger", "early_signal", "impact", "response"),
            minimum=3,
            maximum=5,
        ),
    }
    for index, perspective in enumerate(normalized["perspectives"]):
        severity = perspective["severity"].lower()
        if severity not in {"low", "medium", "high", "critical"}:
            raise ContractError(f"analysis.perspectives[{index}].severity is invalid")
        perspective["severity"] = severity
    return normalized


def validate_decision(value: Any) -> dict[str, Any]:
    root = _object(value, "decision")
    recommendation = _clean_text(root.get("recommendation"), "decision.recommendation", limit=20)
    if recommendation not in {"GO", "CONDITIONAL_GO", "NO_GO"}:
        raise ContractError("decision.recommendation is invalid")
    return {
        "recommendation": recommendation,
        "rationale": _clean_text(root.get("rationale"), "decision.rationale", limit=1_500),
        "gates": _object_list(
            root.get("gates"),
            "decision.gates",
            fields=("condition", "owner", "deadline", "fallback"),
            minimum=3,
            maximum=6,
        ),
        "next_48h": _string_list(
            root.get("next_48h"), "decision.next_48h", minimum=3, maximum=8
        ),
        "stop_conditions": _string_list(
            root.get("stop_conditions"),
            "decision.stop_conditions",
            minimum=2,
            maximum=6,
        ),
    }


def _object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{field} must be an object")
    return value


def _string_list(
    value: Any, field: str, *, minimum: int, maximum: int
) -> list[str]:
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ContractError(f"{field} must contain {minimum} to {maximum} items")
    return [_clean_text(item, f"{field}[{index}]", limit=500) for index, item in enumerate(value)]


def _object_list(
    value: Any,
    field: str,
    *,
    fields: tuple[str, ...],
    minimum: int,
    maximum: int,
) -> list[dict[str, str]]:
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ContractError(f"{field} must contain {minimum} to {maximum} items")
    normalized: list[dict[str, str]] = []
    for index, item in enumerate(value):
        obj = _object(item, f"{field}[{index}]")
        normalized.append(
            {
                key: _clean_text(obj.get(key), f"{field}[{index}].{key}", limit=800)
                for key in fields
            }
        )
    return normalized
