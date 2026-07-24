"""Workflow for scoring one existing AI-system run."""

from __future__ import annotations

import json

from pydantic import ValidationError

from hy3_evalforge.core.aggregation import aggregate_scores
from hy3_evalforge.core.evidence import validate_evidence
from hy3_evalforge.core.paths import ArtifactStore
from hy3_evalforge.core.redaction import redact_text
from hy3_evalforge.core.rule_engine import evaluate
from hy3_evalforge.errors import ErrorCode, EvalForgeError
from hy3_evalforge.models.cases import EvalCase
from hy3_evalforge.models.judgments import ScoreRunResult, SingleJudgment
from hy3_evalforge.models.runs import RunResponse
from hy3_evalforge.models.spec import EvalSpec
from hy3_evalforge.prompts.score_run import build_request
from hy3_evalforge.providers.base import Provider, ProviderRequest
from hy3_evalforge.services.spec_designer import _validation_messages

MODE_SETTINGS = {
    "fast": ("no_think", 1),
    "balanced": ("low", 2),
    "rigorous": ("high", 3),
}


class RunScorer:
    """Keep hard gates and semantic scores separate in one auditable scorecard."""

    def __init__(
        self,
        store: ArtifactStore,
        provider: Provider,
        *,
        max_calls: int,
        extra_secrets: tuple[str, ...] = (),
    ) -> None:
        self._store = store
        self._provider = provider
        self._max_calls = max_calls
        self._extra_secrets = extra_secrets

    async def score(
        self,
        *,
        project_dir: str,
        run_name: str,
        responses_path: str,
        mode: str,
        allow_expensive: bool,
        overwrite: bool,
    ) -> ScoreRunResult:
        """Score a JSONL run after strict case alignment and budget validation."""
        if mode not in MODE_SETTINGS or not _valid_run_name(run_name):
            raise EvalForgeError(ErrorCode.INPUT_ERROR, "run_name or mode is invalid.")
        project = self._store.resolve(project_dir, must_exist=True)
        spec = EvalSpec.model_validate(self._store.read_json(project / "eval_spec.json"))
        cases = _read_jsonl(self._store, project / "cases.jsonl", EvalCase)
        responses = _read_jsonl(self._store, responses_path, RunResponse)
        _validate_alignment(cases, responses)
        effort, repetitions = MODE_SETTINGS[mode]
        estimated_calls = len(cases) * repetitions
        if estimated_calls > self._max_calls and not allow_expensive:
            raise EvalForgeError(
                ErrorCode.BUDGET_EXCEEDED,
                "Requested semantic judgments exceed the configured model-call budget.",
            )
        response_by_case = {response.case_id: response for response in responses}
        entries: list[dict[str, object]] = []
        manual_review_cases: list[str] = []
        for case in cases:
            response = response_by_case[case.case_id]
            hard_results = evaluate(case.hard_checks, response.output, response.tool_calls)
            judgments = [
                await self._judge(spec, case, response.output, effort) for _ in range(repetitions)
            ]
            dimensions = [item for item in spec.dimensions if item.name in case.dimensions]
            semantic = aggregate_scores(judgments, dimensions)
            if mode == "rigorous" and semantic["agreement"] < 2 / 3:
                manual_review_cases.append(case.case_id)
            entries.append(
                {
                    "case_id": case.case_id,
                    "hard_checks": [item.model_dump() for item in hard_results],
                    "semantic": semantic,
                }
            )
        run_score = _weighted_run_score(entries, cases)
        critical_failures = sum(
            not result["passed"] and result["severity"] == "critical"
            for entry in entries
            for result in entry["hard_checks"]
        )
        scorecard = {
            "spec_id": spec.spec_id,
            "run_name": run_name,
            "responses_path": str(self._store.resolve(responses_path)),
            "entries": entries,
            "run_score": run_score,
            "critical_failures": critical_failures,
            "manual_review_cases": manual_review_cases,
        }
        runs_directory = self._store.resolve(project / "runs")
        runs_directory.mkdir(exist_ok=True)
        path = self._store.write_json(
            project / "runs" / f"{run_name}.scorecard.json",
            scorecard,
            overwrite=overwrite,
        )
        return ScoreRunResult(
            run_name=run_name,
            scorecard_path=str(path.relative_to(project)),
            run_score=run_score,
            critical_failures=critical_failures,
            manual_review_cases=manual_review_cases,
        )

    async def _judge(
        self,
        spec: EvalSpec,
        case: EvalCase,
        output: str,
        effort: str,
    ) -> SingleJudgment:
        redacted_output = redact_text(output, additional_secrets=self._extra_secrets)
        request = build_request(
            spec,
            case,
            redacted_output,
            effort,
        )
        errors: list[str] | None = None
        for attempt in range(2):
            active = request if attempt == 0 else _repair_request(request, errors or [])
            response = await self._provider.complete(active)
            try:
                judgment = SingleJudgment.model_validate(json.loads(response.content))
                if judgment.case_id != case.case_id:
                    raise ValueError("judgment case_id does not match the requested case")
                if set(judgment.dimension_scores) != set(case.dimensions):
                    raise ValueError("judgment dimensions do not match the requested case")
                validate_evidence(judgment.evidence, redacted_output)
                return judgment
            except (ValidationError, json.JSONDecodeError) as exc:
                errors = _validation_messages(exc)
            except (ValueError, EvalForgeError) as exc:
                errors = [str(exc)]
        raise EvalForgeError(
            ErrorCode.HY3_OUTPUT_INVALID,
            "Hy3 did not return a valid semantic judgment after one repair attempt.",
        )


def _read_jsonl(store: ArtifactStore, path, model):
    records = []
    for line_number, line in enumerate(store.read_text(path).splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(model.model_validate(json.loads(line)))
        except (ValidationError, json.JSONDecodeError) as exc:
            raise EvalForgeError(
                ErrorCode.INPUT_ERROR,
                f"Invalid JSONL record at line {line_number}.",
            ) from exc
    return records


def _validate_alignment(cases, responses) -> None:
    case_ids = [case.case_id for case in cases]
    response_ids = [response.case_id for response in responses]
    if (
        not cases
        or len(case_ids) != len(set(case_ids))
        or len(response_ids) != len(set(response_ids))
        or set(case_ids) != set(response_ids)
    ):
        raise EvalForgeError(
            ErrorCode.INPUT_ERROR,
            "responses must map one-to-one to the generated case collection.",
        )


def _weighted_run_score(entries, cases) -> float:
    weights = {case.case_id: case.weight for case in cases}
    return sum(
        entry["semantic"]["semantic_score"] * weights[entry["case_id"]] for entry in entries
    ) / sum(weights.values())


def _repair_request(request: ProviderRequest, errors: list[str]) -> ProviderRequest:
    return ProviderRequest(
        request.system_prompt + " Return corrected JSON only.",
        request.user_prompt + " Validation errors: " + "; ".join(errors),
        request.reasoning_effort,
    )


def _valid_run_name(value: str) -> bool:
    return bool(value) and value.replace("_", "").replace("-", "").isalnum()
