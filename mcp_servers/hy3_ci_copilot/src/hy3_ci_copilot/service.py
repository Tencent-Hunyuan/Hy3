from __future__ import annotations

import asyncio
import json
from typing import Any

from hy3_ci_copilot.config import Settings
from hy3_ci_copilot.context import (
    PathPolicy,
    parse_workflow,
    read_text_excerpt,
    repository_context,
    signal_diff,
)
from hy3_ci_copilot.errors import InputFileError
from hy3_ci_copilot.hy3_client import Hy3Client, ReasoningEffort
from hy3_ci_copilot.prompts import (
    BASE_SYSTEM_PROMPT,
    COMPARE_TASK,
    DIAGNOSE_TASK,
    FIX_PLAN_TASK,
    WORKFLOW_REVIEW_TASK,
    OutputLanguage,
    make_prompt,
)
from hy3_ci_copilot.security import sanitize_untrusted_text, truncate_middle


def _runtime(settings: Settings | None) -> tuple[Settings, PathPolicy]:
    current = settings or Settings.from_env()
    return current, PathPolicy(current.allowed_roots)


async def _complete(
    settings: Settings,
    task: str,
    data: dict[str, Any],
    output_language: OutputLanguage,
    reasoning_effort: ReasoningEffort,
    client: Hy3Client | None,
) -> str:
    prompt = make_prompt(task, data, output_language)
    if len(prompt) > settings.max_input_chars:
        excerpt_budget = settings.max_input_chars // 2
        while True:
            excerpt = truncate_middle(prompt, excerpt_budget, "serialized evidence")
            candidate = json.dumps(
                {
                    "task": task,
                    "response_language": output_language,
                    "notice": "The serialized evidence was truncated to the input limit.",
                    "untrusted_serialized_evidence_excerpt": excerpt,
                },
                ensure_ascii=False,
            )
            if len(candidate) <= settings.max_input_chars or excerpt_budget == 0:
                prompt = candidate
                break
            excerpt_budget = max(
                0,
                excerpt_budget - (len(candidate) - settings.max_input_chars),
            )
    return await (client or Hy3Client(settings)).complete(
        system_prompt=BASE_SYSTEM_PROMPT,
        user_prompt=prompt,
        reasoning_effort=reasoning_effort,
    )


async def diagnose_ci_failure_service(
    *,
    log_path: str,
    repository_path: str,
    focus: str,
    output_language: OutputLanguage,
    reasoning_effort: ReasoningEffort,
    settings: Settings | None = None,
    client: Hy3Client | None = None,
) -> str:
    current, policy = _runtime(settings)
    repository = policy.repository(repository_path)
    log_path_resolved = policy.file(log_path, repository)
    log, context = await asyncio.gather(
        asyncio.to_thread(
            read_text_excerpt,
            log_path_resolved,
            repository,
            int(current.max_input_chars * 0.65),
        ),
        asyncio.to_thread(
            repository_context,
            repository,
            int(current.max_input_chars * 0.24),
            current.allowed_roots,
        ),
    )
    data = {
        "focus": truncate_middle(sanitize_untrusted_text(focus), 4000, "focus"),
        "log": {
            "path": log.relative_path,
            "original_bytes": log.original_bytes,
            "truncated": log.truncated,
            "content": log.content,
        },
        "repository": context,
    }
    return await _complete(current, DIAGNOSE_TASK, data, output_language, reasoning_effort, client)


async def compare_ci_runs_service(
    *,
    failed_log_path: str,
    successful_log_path: str,
    repository_path: str,
    focus: str,
    output_language: OutputLanguage,
    reasoning_effort: ReasoningEffort,
    settings: Settings | None = None,
    client: Hy3Client | None = None,
) -> str:
    current, policy = _runtime(settings)
    repository = policy.repository(repository_path)
    per_log = int(current.max_input_chars * 0.34)
    failed_path = policy.file(failed_log_path, repository)
    successful_path = policy.file(successful_log_path, repository)
    if failed_path == successful_path:
        raise InputFileError("Failed and successful logs must be different files.")
    failed, successful, context = await asyncio.gather(
        asyncio.to_thread(read_text_excerpt, failed_path, repository, per_log),
        asyncio.to_thread(read_text_excerpt, successful_path, repository, per_log),
        asyncio.to_thread(
            repository_context,
            repository,
            int(current.max_input_chars * 0.14),
            current.allowed_roots,
        ),
    )
    data = {
        "focus": truncate_middle(sanitize_untrusted_text(focus), 4000, "focus"),
        "failed_run": {
            "path": failed.relative_path,
            "truncated": failed.truncated,
            "content": failed.content,
        },
        "successful_run": {
            "path": successful.relative_path,
            "truncated": successful.truncated,
            "content": successful.content,
        },
        "signal_diff": signal_diff(successful.content, failed.content),
        "repository": context,
    }
    return await _complete(current, COMPARE_TASK, data, output_language, reasoning_effort, client)


async def review_ci_workflow_service(
    *,
    workflow_path: str,
    repository_path: str,
    focus: str,
    output_language: OutputLanguage,
    reasoning_effort: ReasoningEffort,
    settings: Settings | None = None,
    client: Hy3Client | None = None,
) -> str:
    current, policy = _runtime(settings)
    repository = policy.repository(repository_path)
    workflow_path_resolved = policy.file(workflow_path, repository)
    workflow, context = await asyncio.gather(
        asyncio.to_thread(
            read_text_excerpt,
            workflow_path_resolved,
            repository,
            int(current.max_input_chars * 0.55),
        ),
        asyncio.to_thread(
            repository_context,
            repository,
            int(current.max_input_chars * 0.32),
            current.allowed_roots,
        ),
    )
    parsed = (
        {"notice": "Structure was not parsed because the workflow excerpt is truncated."}
        if workflow.truncated
        else parse_workflow(workflow.content)
    )
    data = {
        "focus": truncate_middle(sanitize_untrusted_text(focus), 4000, "focus"),
        "workflow": {
            "path": workflow.relative_path,
            "truncated": workflow.truncated,
            "structure": parsed,
            "content": workflow.content,
        },
        "repository": context,
    }
    return await _complete(
        current, WORKFLOW_REVIEW_TASK, data, output_language, reasoning_effort, client
    )


async def build_ci_fix_plan_service(
    *,
    diagnosis: str,
    repository_path: str,
    constraints: str,
    output_language: OutputLanguage,
    reasoning_effort: ReasoningEffort,
    settings: Settings | None = None,
    client: Hy3Client | None = None,
) -> str:
    current, policy = _runtime(settings)
    repository = policy.repository(repository_path)
    context = await asyncio.to_thread(
        repository_context,
        repository,
        int(current.max_input_chars * 0.34),
        current.allowed_roots,
    )
    data = {
        "diagnosis": truncate_middle(
            sanitize_untrusted_text(diagnosis), int(current.max_input_chars * 0.52), "diagnosis"
        ),
        "constraints": truncate_middle(sanitize_untrusted_text(constraints), 8000, "constraints"),
        "repository": context,
    }
    return await _complete(current, FIX_PLAN_TASK, data, output_language, reasoning_effort, client)
