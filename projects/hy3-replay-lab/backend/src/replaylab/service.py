from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from replaylab.providers import AnalysisProvider
from replaylab.schemas import AnalysisDraft, AnalysisMetadata, ReplayReport, TaskSpec
from replaylab.security import redact_analysis_draft, redact_task_spec
from replaylab.validation import OutputValidationError, validate_analysis_draft


class ProviderOutputError(ValueError):
    """Raised when a provider response is not parseable structured output."""


class ReplayLabService:
    def __init__(self, provider: AnalysisProvider) -> None:
        self._provider = provider

    async def analyze(self, task: TaskSpec) -> ReplayReport:
        safe_task = redact_task_spec(task)
        raw_draft = await self._provider.analyze(safe_task)
        try:
            draft = _parse_and_validate(safe_task, raw_draft)
        except (ProviderOutputError, OutputValidationError):
            repaired = await self._provider.repair(
                safe_task,
                raw_draft,
                "schema_or_reference_validation_failed",
            )
            try:
                draft = _parse_and_validate(safe_task, repaired)
            except (ProviderOutputError, OutputValidationError) as error:
                raise ProviderOutputError("provider output failed controlled repair") from error
        report_id = _stable_report_id(safe_task, draft)
        metrics = getattr(self._provider, "last_metrics", None)
        return ReplayReport(
            report_id=report_id,
            fixture_id=safe_task.fixture_id,
            task=safe_task.task,
            criteria=safe_task.criteria,
            timeline=safe_task.trace,
            evidence=safe_task.evidence,
            coverage=draft.coverage,
            finding=draft.finding,
            replay_plan=draft.replay_plan,
            metadata=AnalysisMetadata(
                provider=self._provider.name,
                model=self._provider.model,
                mode=self._provider.mode,
                latency_ms=getattr(metrics, "latency_ms", None),
                prompt_tokens=getattr(metrics, "prompt_tokens", None),
                completion_tokens=getattr(metrics, "completion_tokens", None),
                total_tokens=getattr(metrics, "total_tokens", None),
                request_attempts=getattr(metrics, "request_attempts", None) or None,
            ),
        )


def _parse_draft(raw_draft: Mapping[str, Any] | str) -> AnalysisDraft:
    if isinstance(raw_draft, str):
        try:
            payload = json.loads(raw_draft)
        except json.JSONDecodeError as error:
            raise ProviderOutputError("provider returned invalid JSON") from error
    else:
        payload = raw_draft
    try:
        return redact_analysis_draft(AnalysisDraft.model_validate(payload))
    except ValueError as error:
        raise ProviderOutputError("provider returned an invalid replay draft") from error


def _parse_and_validate(task: TaskSpec, raw_draft: Mapping[str, Any] | str) -> AnalysisDraft:
    draft = _parse_draft(raw_draft)
    validate_analysis_draft(task, draft)
    return draft


def _stable_report_id(task: TaskSpec, draft: AnalysisDraft) -> str:
    payload = {
        "task": task.model_dump(mode="json"),
        "draft": draft.model_dump(mode="json"),
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"report_{hashlib.sha256(canonical).hexdigest()[:16]}"
