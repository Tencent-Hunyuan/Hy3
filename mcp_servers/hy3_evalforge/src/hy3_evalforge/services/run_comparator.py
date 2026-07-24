"""Deterministic scorecard comparison and auditable regression reports."""

from __future__ import annotations

import json
import random

from pydantic import ValidationError

from hy3_evalforge.core.bootstrap import mean_difference_interval
from hy3_evalforge.core.paths import ArtifactStore
from hy3_evalforge.core.redaction import redact_text
from hy3_evalforge.errors import ErrorCode, EvalForgeError
from hy3_evalforge.models.cases import EvalCase
from hy3_evalforge.models.reports import CompareRunsResult, ComparisonStatus, PairwiseJudgment
from hy3_evalforge.models.runs import RunResponse
from hy3_evalforge.prompts.compare_runs import build_request
from hy3_evalforge.providers.base import Provider, ProviderRequest


class RunComparator:
    def __init__(
        self,
        store: ArtifactStore,
        provider: Provider | None = None,
        *,
        max_calls: int = 24,
        extra_secrets: tuple[str, ...] = (),
    ) -> None:
        self._store = store
        self._provider = provider
        self._max_calls = max_calls
        self._extra_secrets = extra_secrets

    async def compare_with_pairwise(
        self,
        *,
        project_dir: str,
        baseline_run: str,
        candidate_run: str,
        mode: str,
        practical_delta: float,
        allow_expensive: bool,
        overwrite: bool,
    ) -> CompareRunsResult:
        """Add blinded A/B/TIE judgments to the deterministic comparison report."""
        if self._provider is None:
            raise EvalForgeError(
                ErrorCode.PROVIDER_ERROR, "A Hy3 provider is required for comparison."
            )
        if mode not in {"fast", "balanced", "rigorous"}:
            raise EvalForgeError(ErrorCode.INPUT_ERROR, "mode is invalid.")
        result = self.compare(
            project_dir=project_dir,
            baseline_run=baseline_run,
            candidate_run=candidate_run,
            practical_delta=practical_delta,
            overwrite=overwrite,
        )
        project = self._store.resolve(project_dir, must_exist=True)
        baseline = self._store.read_json(project / "runs" / f"{baseline_run}.scorecard.json")
        candidate = self._store.read_json(project / "runs" / f"{candidate_run}.scorecard.json")
        cases = _read_jsonl(self._store, project / "cases.jsonl", EvalCase)
        if len(cases) > self._max_calls and not allow_expensive:
            raise EvalForgeError(
                ErrorCode.BUDGET_EXCEEDED,
                "Requested pairwise judgments exceed the configured model-call budget.",
            )
        baseline_outputs = _response_map(self._store, baseline["responses_path"])
        candidate_outputs = _response_map(self._store, candidate["responses_path"])
        effort = {"fast": "no_think", "balanced": "low", "rigorous": "high"}[mode]
        generator = random.Random(0)
        wins = {"baseline": 0, "candidate": 0, "tie": 0}
        pairwise = []
        for case in cases:
            swapped = generator.choice([False, True])
            first = candidate_outputs[case.case_id] if swapped else baseline_outputs[case.case_id]
            second = baseline_outputs[case.case_id] if swapped else candidate_outputs[case.case_id]
            redacted_first = redact_text(first, additional_secrets=self._extra_secrets)
            redacted_second = redact_text(second, additional_secrets=self._extra_secrets)
            judgment = await self._judge_pairwise(
                build_request(case, redacted_first, redacted_second, effort),
                redacted_first,
                redacted_second,
            )
            winner = _map_winner(judgment.winner, swapped)
            wins[winner] += 1
            pairwise.append(
                {
                    "case_id": case.case_id,
                    "winner": winner,
                    "swapped": swapped,
                    "evidence": [item.model_dump() for item in judgment.evidence],
                }
            )
        report = self._store.read_json(project / result.json_path)
        report["pairwise"] = {"wins": wins, "judgments": pairwise}
        self._store.write_json(project / result.json_path, report, overwrite=True)
        self._store.write_text(
            project / result.report_path,
            _markdown_report(result.status.value, result.confidence_interval, wins),
            overwrite=True,
        )
        return result

    async def _judge_pairwise(
        self, request: ProviderRequest, first: str, second: str
    ) -> PairwiseJudgment:
        errors: list[str] | None = None
        for attempt in range(2):
            active = request if attempt == 0 else _repair_request(request, errors or [])
            response = await self._provider.complete(active)
            try:
                judgment = PairwiseJudgment.model_validate(json.loads(response.content))
                if any(
                    item.quote not in first and item.quote not in second
                    for item in judgment.evidence
                ):
                    raise EvalForgeError(
                        ErrorCode.EVIDENCE_INVALID,
                        "Pairwise evidence is not present in either output.",
                    )
                return judgment
            except (ValidationError, json.JSONDecodeError) as exc:
                errors = [str(exc)]
            except EvalForgeError as exc:
                errors = [exc.message]
        raise EvalForgeError(
            ErrorCode.HY3_OUTPUT_INVALID,
            "Hy3 did not return a valid pairwise judgment after one repair attempt.",
        )

    def compare(
        self,
        *,
        project_dir: str,
        baseline_run: str,
        candidate_run: str,
        practical_delta: float,
        overwrite: bool,
    ) -> CompareRunsResult:
        project = self._store.resolve(project_dir, must_exist=True)
        baseline = self._store.read_json(project / "runs" / f"{baseline_run}.scorecard.json")
        candidate = self._store.read_json(project / "runs" / f"{candidate_run}.scorecard.json")
        if baseline["spec_id"] != candidate["spec_id"]:
            raise EvalForgeError(ErrorCode.INPUT_ERROR, "Runs must use the same spec_id.")
        base_entries = {entry["case_id"]: entry for entry in baseline["entries"]}
        candidate_entries = {entry["case_id"]: entry for entry in candidate["entries"]}
        if set(base_entries) != set(candidate_entries):
            raise EvalForgeError(ErrorCode.INPUT_ERROR, "Runs must use the same case IDs.")
        new_critical = _new_critical_failures(base_entries, candidate_entries)
        differences = [
            candidate_entries[case_id]["semantic"]["semantic_score"]
            - base_entries[case_id]["semantic"]["semantic_score"]
            for case_id in sorted(base_entries)
        ]
        interval = mean_difference_interval(differences, seed=0) if len(differences) >= 10 else None
        status = _status(new_critical, interval, practical_delta)
        report = {
            "status": status.value,
            "spec_id": baseline["spec_id"],
            "baseline_run": baseline_run,
            "candidate_run": candidate_run,
            "new_critical_failures": new_critical,
            "confidence_interval": interval,
        }
        json_path = self._store.write_json(
            project / "runs" / f"{baseline_run}_vs_{candidate_run}.comparison.json",
            report,
            overwrite=overwrite,
        )
        markdown = _markdown_report(status.value, interval)
        report_path = self._store.write_text(
            project / "runs" / f"{baseline_run}_vs_{candidate_run}.report.md",
            markdown,
            overwrite=overwrite,
        )
        return CompareRunsResult(
            status=status,
            report_path=str(report_path.relative_to(project)),
            json_path=str(json_path.relative_to(project)),
            confidence_interval=interval,
        )


def _new_critical_failures(baseline_entries, candidate_entries) -> int:
    def failed(entry):
        return {
            item["check_type"]
            for item in entry["hard_checks"]
            if not item["passed"] and item["severity"] == "critical"
        }

    return sum(
        bool(failed(candidate_entries[key]) - failed(baseline_entries[key]))
        for key in baseline_entries
    )


def _status(new_critical: int, interval, delta: float) -> ComparisonStatus:
    if new_critical:
        return ComparisonStatus.BLOCKED
    if interval is None:
        return ComparisonStatus.INCONCLUSIVE
    low, high = interval
    if high < -delta:
        return ComparisonStatus.REGRESSED
    if low > delta:
        return ComparisonStatus.IMPROVED
    if low >= -delta and high <= delta:
        return ComparisonStatus.NO_MATERIAL_CHANGE
    return ComparisonStatus.INCONCLUSIVE


def _read_jsonl(store: ArtifactStore, path, model):
    return [
        model.model_validate(json.loads(line))
        for line in store.read_text(path).splitlines()
        if line
    ]


def _response_map(store: ArtifactStore, path) -> dict[str, str]:
    return {item.case_id: item.output for item in _read_jsonl(store, path, RunResponse)}


def _map_winner(winner: str, swapped: bool) -> str:
    if winner == "TIE":
        return "tie"
    if (winner == "A") != swapped:
        return "baseline"
    return "candidate"


def _repair_request(request: ProviderRequest, errors: list[str]) -> ProviderRequest:
    return ProviderRequest(
        request.system_prompt + " Return corrected JSON only.",
        request.user_prompt + " Validation errors: " + "; ".join(errors),
        request.reasoning_effort,
    )


def _markdown_report(status: str, interval, wins: dict[str, int] | None = None) -> str:
    confidence_text = (
        str(interval) if interval is not None else "INCONCLUSIVE (fewer than 10 cases)"
    )
    pairwise = ""
    if wins is not None:
        pairwise = (
            "\nPairwise (blinded): "
            f"baseline {wins['baseline']}, candidate {wins['candidate']}, tie {wins['tie']}.\n"
        )
    return (
        f"# EvalForge Comparison\n\nStatus: **{status}**\n\n95% CI: {confidence_text}\n{pairwise}"
    )
