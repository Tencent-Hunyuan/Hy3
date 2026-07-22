"""Tool implementations separated from MCP transport for deterministic testing."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Literal, Protocol

from .audit import audit_locally, iter_operations
from .diff_engine import compare_specs
from .errors import SpecInputError
from .hy3_client import Hy3Client, ModelReply
from .models import AuditResult, BreakingChangeResult, ContractTestResult
from .prompts import AUDIT_SYSTEM, DIFF_SYSTEM, TEST_SYSTEM
from .settings import Settings
from .spec_loader import HTTP_METHODS, LoadedSpec, compact_for_model, load_spec


class CompletionClient(Protocol):
    async def complete(self, *, system: str, user: str) -> ModelReply: ...


def _client(settings: Settings, supplied: CompletionClient | None) -> CompletionClient:
    return supplied if supplied is not None else Hy3Client(settings)


def _operation_names(spec: LoadedSpec, selected_paths: Sequence[str] | None) -> list[str]:
    operations = [
        (path, f"{method.upper()} {path}")
        for path, method, _operation, _parameters in iter_operations(spec.document)
    ]
    if not operations:
        raise SpecInputError("The specification contains no operations to generate tests for")

    requested: set[str] = set()
    for selector in selected_paths or []:
        normalized = selector.strip()
        parts = normalized.split(maxsplit=1)
        if len(parts) == 2 and parts[0].lower() in HTTP_METHODS:
            normalized = f"{parts[0].upper()} {parts[1]}"
        if normalized:
            requested.add(normalized)
    if not requested:
        return [name for _path, name in operations]

    matched_selectors: set[str] = set()
    names: list[str] = []
    for path, name in operations:
        selectors = {path, name}
        matches = requested & selectors
        if matches:
            matched_selectors.update(matches)
            names.append(name)
    unmatched = sorted(requested - matched_selectors)
    if unmatched:
        rendered = ", ".join(unmatched[:5])
        suffix = " ..." if len(unmatched) > 5 else ""
        raise SpecInputError(f"selected_paths did not match an operation: {rendered}{suffix}")
    return names


def _strip_code_fence(content: str) -> str:
    match = re.fullmatch(
        r"\s*```(?:python|javascript|typescript|js|ts)?\s*\n(.*?)\n```\s*", content, re.S
    )
    return match.group(1).strip() if match else content.strip()


async def audit_openapi_service(
    *,
    spec_path: str | None,
    spec_text: str | None,
    focus: str,
    settings: Settings,
    client: CompletionClient | None = None,
) -> AuditResult:
    spec = load_spec(spec_path=spec_path, spec_text=spec_text, settings=settings)
    local_findings = audit_locally(spec)
    prompt = f"""Audit focus: {focus}
Specification label: {spec.label}
Deterministic findings (these are evidence, verify their implications):
{json.dumps([item.model_dump() for item in local_findings], ensure_ascii=False)}

<UNTRUSTED_OPENAPI_DATA>
{compact_for_model(spec, settings.max_model_chars)}
</UNTRUSTED_OPENAPI_DATA>
"""
    reply = await _client(settings, client).complete(system=AUDIT_SYSTEM, user=prompt)
    return AuditResult(
        specification=spec.title,
        openapi_version=spec.version,
        operation_count=spec.operation_count,
        local_findings=local_findings,
        hy3_analysis=reply.content,
        model=settings.model,
        usage=reply.usage,
    )


async def detect_breaking_changes_service(
    *,
    old_spec_path: str | None,
    old_spec_text: str | None,
    new_spec_path: str | None,
    new_spec_text: str | None,
    include_compatible: bool,
    settings: Settings,
    client: CompletionClient | None = None,
) -> BreakingChangeResult:
    old = load_spec(
        spec_path=old_spec_path,
        spec_text=old_spec_text,
        settings=settings,
        label="old-openapi.yaml",
    )
    new = load_spec(
        spec_path=new_spec_path,
        spec_text=new_spec_text,
        settings=settings,
        label="new-openapi.yaml",
    )
    all_changes = compare_specs(old, new)
    visible_changes = (
        all_changes
        if include_compatible
        else [item for item in all_changes if item.kind != "compatible"]
    )
    half_budget = max(2_000, settings.max_model_chars // 2)
    prompt = f"""Explain the consumer impact and propose a safe migration plan.
Deterministic changes:
{json.dumps([item.model_dump() for item in all_changes], ensure_ascii=False)}

<UNTRUSTED_OLD_OPENAPI_DATA>
{compact_for_model(old, half_budget)}
</UNTRUSTED_OLD_OPENAPI_DATA>

<UNTRUSTED_NEW_OPENAPI_DATA>
{compact_for_model(new, half_budget)}
</UNTRUSTED_NEW_OPENAPI_DATA>
"""
    reply = await _client(settings, client).complete(system=DIFF_SYSTEM, user=prompt)
    return BreakingChangeResult(
        old_specification=old.title,
        new_specification=new.title,
        breaking_count=sum(item.kind == "breaking" for item in all_changes),
        warning_count=sum(item.kind == "warning" for item in all_changes),
        compatible_count=sum(item.kind == "compatible" for item in all_changes),
        changes=visible_changes,
        hy3_migration_analysis=reply.content,
        model=settings.model,
        usage=reply.usage,
    )


async def generate_contract_tests_service(
    *,
    spec_path: str | None,
    spec_text: str | None,
    framework: Literal["pytest", "jest"],
    selected_paths: Sequence[str] | None,
    settings: Settings,
    client: CompletionClient | None = None,
) -> ContractTestResult:
    spec = load_spec(spec_path=spec_path, spec_text=spec_text, settings=settings)
    operations = _operation_names(spec, selected_paths)
    if len(operations) > 20:
        raise SpecInputError(
            "The selection contains more than 20 operations; use selected_paths to narrow it"
        )
    framework_instruction = (
        "Generate one Python module using pytest and httpx."
        if framework == "pytest"
        else "Generate one TypeScript test module using Jest and native fetch."
    )
    prompt = f"""{framework_instruction}
Selected operations: {json.dumps(operations, ensure_ascii=False)}
Cover a representative success case plus validation, authentication, and boundary failures that
are justified by the contract. Use environment variables API_BASE_URL and API_TEST_TOKEN.
Return only the complete source file with no Markdown fence.

<UNTRUSTED_OPENAPI_DATA>
{compact_for_model(spec, settings.max_model_chars)}
</UNTRUSTED_OPENAPI_DATA>
"""
    reply = await _client(settings, client).complete(system=TEST_SYSTEM, user=prompt)
    instructions = (
        [
            "python -m pip install pytest httpx",
            "Set API_BASE_URL and optionally API_TEST_TOKEN",
            "pytest -q generated_contract_test.py",
        ]
        if framework == "pytest"
        else [
            "npm install --save-dev jest ts-jest @types/jest typescript",
            "Set API_BASE_URL and optionally API_TEST_TOKEN",
            "npx jest generated-contract.test.ts",
        ]
    )
    return ContractTestResult(
        specification=spec.title,
        framework=framework,
        selected_operations=operations,
        generated_code=_strip_code_fence(reply.content),
        run_instructions=instructions,
        model=settings.model,
        usage=reply.usage,
    )
