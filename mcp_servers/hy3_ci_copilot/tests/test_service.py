from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from hy3_ci_copilot.errors import InputFileError
from hy3_ci_copilot.service import (
    build_ci_fix_plan_service,
    compare_ci_runs_service,
    diagnose_ci_failure_service,
    review_ci_workflow_service,
)


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def complete(self, **kwargs) -> str:
        self.calls.append(kwargs)
        return "Hy3 result"


@pytest.mark.asyncio
async def test_all_services_call_hy3_with_sanitized_evidence(repository: Path, settings) -> None:
    (repository / "failed.log").write_text(
        "API_TOKEN=top-secret\nERROR dependency missing\n", encoding="utf-8"
    )
    client = RecordingClient()

    diagnosis = await diagnose_ci_failure_service(
        log_path="failed.log",
        repository_path=str(repository),
        focus="dependency install",
        output_language="en",
        reasoning_effort="high",
        settings=settings,
        client=client,
    )
    comparison = await compare_ci_runs_service(
        failed_log_path="failed.log",
        successful_log_path="successful.log",
        repository_path=str(repository),
        focus="",
        output_language="en",
        reasoning_effort="high",
        settings=settings,
        client=client,
    )
    review = await review_ci_workflow_service(
        workflow_path=".github/workflows/ci.yml",
        repository_path=str(repository),
        focus="reproducibility",
        output_language="en",
        reasoning_effort="low",
        settings=settings,
        client=client,
    )
    plan = await build_ci_fix_plan_service(
        diagnosis="The dependency is incompatible.",
        repository_path=str(repository),
        constraints="Keep Python 3.12 support.",
        output_language="en",
        reasoning_effort="high",
        settings=settings,
        client=client,
    )

    assert {diagnosis, comparison, review, plan} == {"Hy3 result"}
    assert len(client.calls) == 4
    assert all(call["system_prompt"] for call in client.calls)
    assert all(call["reasoning_effort"] in {"low", "high"} for call in client.calls)
    assert "top-secret" not in "\n".join(call["user_prompt"] for call in client.calls)
    assert "[REDACTED]" in client.calls[0]["user_prompt"]


@pytest.mark.asyncio
async def test_compare_rejects_the_same_log(repository: Path, settings) -> None:
    with pytest.raises(InputFileError, match="different files"):
        await compare_ci_runs_service(
            failed_log_path="failed.log",
            successful_log_path="failed.log",
            repository_path=str(repository),
            focus="",
            output_language="en",
            reasoning_effort="high",
            settings=settings,
            client=RecordingClient(),
        )


@pytest.mark.asyncio
async def test_empty_supplemental_manifest_is_skipped(repository: Path, settings) -> None:
    (repository / "requirements.txt").write_text("", encoding="utf-8")
    client = RecordingClient()

    result = await diagnose_ci_failure_service(
        log_path="failed.log",
        repository_path=str(repository),
        focus="",
        output_language="en",
        reasoning_effort="high",
        settings=settings,
        client=client,
    )

    assert result == "Hy3 result"
    assert "requirements.txt" not in client.calls[0]["user_prompt"]


@pytest.mark.asyncio
async def test_truncated_workflow_and_prompt_budget_are_handled(repository: Path, settings) -> None:
    workflow = repository / ".github" / "workflows" / "ci.yml"
    workflow.write_text("name: CI\n" + ('# many comments \\" quoted\n' * 1200), encoding="utf-8")
    client = RecordingClient()
    small_settings = replace(settings, max_input_chars=10_000)

    result = await review_ci_workflow_service(
        workflow_path=".github/workflows/ci.yml",
        repository_path=str(repository),
        focus="",
        output_language="en",
        reasoning_effort="high",
        settings=small_settings,
        client=client,
    )

    assert result == "Hy3 result"
    assert "not parsed because the workflow excerpt is truncated" in client.calls[0]["user_prompt"]
    assert len(client.calls[0]["user_prompt"]) <= small_settings.max_input_chars
