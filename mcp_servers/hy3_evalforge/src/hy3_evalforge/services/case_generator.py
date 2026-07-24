"""Workflow for generating and validating risk-diverse challenge cases."""

from __future__ import annotations

import json

from pydantic import BaseModel, ValidationError

from hy3_evalforge.core.hashing import ngram_similarity, stable_id
from hy3_evalforge.core.paths import ArtifactStore
from hy3_evalforge.errors import ErrorCode, EvalForgeError
from hy3_evalforge.models.cases import CaseCoverage, EvalCase, EvalCaseDraft, GenerateCasesResult
from hy3_evalforge.models.spec import EvalSpec
from hy3_evalforge.prompts.generate_cases import build_request
from hy3_evalforge.providers.base import Provider, ProviderRequest
from hy3_evalforge.services.spec_designer import _validation_messages

DEFAULT_CATEGORIES = (
    "happy_path",
    "boundary",
    "ambiguous",
    "conflicting_constraints",
    "adversarial",
    "multilingual",
    "long_context",
)


class _CaseResponse(BaseModel):
    cases: list[EvalCaseDraft]


class CaseGenerator:
    """Generate exactly one validated, deduplicated, coverage-complete challenge collection."""

    def __init__(self, store: ArtifactStore, provider: Provider) -> None:
        self._store = store
        self._provider = provider

    async def generate(
        self, *, project_dir: str, count: int, categories: str, seed: int, overwrite: bool
    ) -> GenerateCasesResult:
        if not 4 <= count <= 50:
            raise EvalForgeError(ErrorCode.INPUT_ERROR, "count must be between 4 and 50.")
        project = self._store.resolve(project_dir, must_exist=True)
        spec = EvalSpec.model_validate(self._store.read_json(project / "eval_spec.json"))
        requested_categories = _parse_categories(categories)
        response = await self._complete_and_validate(
            build_request(spec=spec, categories=requested_categories, count=count, seed=seed),
            spec,
            count,
        )
        cases = _assign_ids_and_validate(response.cases)
        coverage = _coverage(cases, spec)
        if coverage.uncovered_dimensions:
            raise EvalForgeError(
                ErrorCode.HY3_OUTPUT_INVALID,
                "Hy3 output did not cover every evaluation dimension after one repair attempt.",
            )
        cases_path = self._store.write_text(
            project / "cases.jsonl",
            "".join(
                json.dumps(case.model_dump(mode="json"), ensure_ascii=False) + "\n"
                for case in cases
            ),
            overwrite=overwrite,
        )
        coverage_path = self._store.write_json(
            project / "case_coverage.json", coverage.model_dump(mode="json"), overwrite=overwrite
        )
        return GenerateCasesResult(
            cases_path=str(cases_path.relative_to(project)),
            coverage_path=str(coverage_path.relative_to(project)),
            case_count=len(cases),
            warnings=[],
        )

    async def _complete_and_validate(
        self, request: ProviderRequest, spec: EvalSpec, count: int
    ) -> _CaseResponse:
        errors: list[str] | None = None
        for attempt in range(2):
            active = request if attempt == 0 else _repair_request(request, errors or [])
            response = await self._provider.complete(active)
            try:
                parsed = _CaseResponse.model_validate(json.loads(response.content))
                _validate_case_collection(parsed.cases, spec, count)
                return parsed
            except (ValidationError, json.JSONDecodeError, ValueError) as exc:
                errors = (
                    _validation_messages(exc) if not isinstance(exc, ValueError) else [str(exc)]
                )
        raise EvalForgeError(
            ErrorCode.HY3_OUTPUT_INVALID, "Hy3 did not return valid cases after one repair."
        )


def _parse_categories(raw: str) -> list[str]:
    categories = (
        [part.strip() for part in raw.split(",") if part.strip()]
        if raw
        else list(DEFAULT_CATEGORIES)
    )
    if not categories or len(set(categories)) != len(categories):
        raise EvalForgeError(
            ErrorCode.INPUT_ERROR, "categories must be a non-empty unique comma-separated list."
        )
    return categories


def _repair_request(request: ProviderRequest, errors: list[str]) -> ProviderRequest:
    return ProviderRequest(
        request.system_prompt + "\nReturn corrected JSON only.",
        request.user_prompt + "\nValidation errors: " + "; ".join(errors),
        request.reasoning_effort,
    )


def _validate_case_collection(cases: list[EvalCaseDraft], spec: EvalSpec, count: int) -> None:
    if len(cases) != count:
        raise ValueError(f"cases must contain exactly {count} items")
    known_dimensions = {dimension.name for dimension in spec.dimensions}
    for case in cases:
        if not set(case.dimensions).issubset(known_dimensions):
            raise ValueError("case references an unknown evaluation dimension")


def _assign_ids_and_validate(cases: list[EvalCaseDraft]) -> list[EvalCase]:
    output: list[EvalCase] = []
    seen_inputs: list[str] = []
    for draft in cases:
        if any(ngram_similarity(draft.input, previous) >= 0.92 for previous in seen_inputs):
            raise EvalForgeError(
                ErrorCode.HY3_OUTPUT_INVALID, "Generated cases contain near-duplicate inputs."
            )
        seen_inputs.append(draft.input)
        payload = draft.model_dump(mode="json")
        output.append(EvalCase(**payload, case_id=stable_id("case", payload)))
    if len({case.case_id for case in output}) != len(output):
        raise EvalForgeError(
            ErrorCode.HY3_OUTPUT_INVALID, "Generated cases contain duplicate stable IDs."
        )
    return output


def _coverage(cases: list[EvalCase], spec: EvalSpec) -> CaseCoverage:
    mapping = {dimension.name: [] for dimension in spec.dimensions}
    for case in cases:
        for dimension in case.dimensions:
            mapping[dimension].append(case.case_id)
    return CaseCoverage(
        dimension_cases=mapping,
        uncovered_dimensions=[name for name, case_ids in mapping.items() if not case_ids],
    )
