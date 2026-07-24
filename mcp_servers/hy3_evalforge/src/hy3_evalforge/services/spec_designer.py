"""Workflow for generating, validating, and persisting evaluation specifications."""

from __future__ import annotations

import json

from pydantic import ValidationError

from hy3_evalforge.core.hashing import stable_id
from hy3_evalforge.core.paths import ArtifactStore
from hy3_evalforge.core.redaction import redact_text
from hy3_evalforge.errors import ErrorCode, EvalForgeError
from hy3_evalforge.models.spec import (
    DesignSpecResult,
    EvalSpec,
    EvalSpecDraft,
    normalize_dimension_weights,
)
from hy3_evalforge.prompts.design_spec import build_request
from hy3_evalforge.providers.base import Provider, ProviderRequest


class SpecDesigner:
    """Generate an EvalSpec with one bounded model-format repair attempt."""

    def __init__(
        self,
        store: ArtifactStore,
        provider: Provider,
        *,
        extra_secrets: tuple[str, ...] = (),
    ) -> None:
        self._store = store
        self._provider = provider
        self._extra_secrets = extra_secrets

    async def design(
        self,
        *,
        project_dir: str,
        goal: str,
        success_criteria: str,
        failure_examples: str | None,
        policies: str | None,
        output_language: str,
        overwrite: bool,
    ) -> DesignSpecResult:
        """Turn a bounded natural-language target into a normalized persisted specification."""
        self._validate_text_input(goal, "goal")
        self._validate_text_input(success_criteria, "success_criteria")
        for name, value in (("failure_examples", failure_examples), ("policies", policies)):
            if value is not None:
                self._validate_text_input(value, name)
        if output_language not in {"zh-CN", "en"}:
            raise EvalForgeError(ErrorCode.INPUT_ERROR, "output_language must be zh-CN or en.")
        project = self._store.resolve(project_dir, must_exist=True)
        if not project.is_dir():
            raise EvalForgeError(
                ErrorCode.INPUT_ERROR, "project_dir must be an existing directory."
            )
        request = build_request(
            goal=redact_text(goal, additional_secrets=self._extra_secrets),
            success_criteria=redact_text(success_criteria, additional_secrets=self._extra_secrets),
            failure_examples=self._redact_optional(failure_examples),
            policies=self._redact_optional(policies),
            output_language=output_language,
        )
        draft = await self._complete_and_validate(request)
        normalized_draft = draft.model_copy(
            update={"dimensions": normalize_dimension_weights(draft.dimensions)}
        )
        spec_id = stable_id("spec", normalized_draft)
        spec = EvalSpec(**normalized_draft.model_dump(), spec_id=spec_id)
        path = self._store.write_json(
            project / "eval_spec.json", spec.model_dump(mode="json"), overwrite=overwrite
        )
        return DesignSpecResult(
            spec_id=spec.spec_id,
            spec_path=str(path.relative_to(project)),
            dimension_count=len(spec.dimensions),
            hard_gate_count=len(spec.hard_gates),
        )

    async def _complete_and_validate(self, request: ProviderRequest) -> EvalSpecDraft:
        """Parse one JSON object and request one repair without echoing the prior model output."""
        errors: list[str] | None = None
        for attempt in range(2):
            active_request = (
                request if attempt == 0 else self._repair_request(request, errors or [])
            )
            response = await self._provider.complete(active_request)
            try:
                return EvalSpecDraft.model_validate(json.loads(response.content))
            except (ValidationError, json.JSONDecodeError) as exc:
                errors = _validation_messages(exc)
        raise EvalForgeError(
            ErrorCode.HY3_OUTPUT_INVALID,
            "Hy3 did not return a valid evaluation specification after one repair attempt.",
        )

    @staticmethod
    def _repair_request(request: ProviderRequest, errors: list[str]) -> ProviderRequest:
        return ProviderRequest(
            system_prompt=(
                request.system_prompt
                + "\nYour previous response was invalid. Return a corrected JSON object only."
            ),
            user_prompt=request.user_prompt + "\nValidation errors: " + "; ".join(errors),
            reasoning_effort=request.reasoning_effort,
        )

    @staticmethod
    def _validate_text_input(value: str, name: str) -> None:
        if not value.strip() or len(value) > 32_000:
            raise EvalForgeError(
                ErrorCode.INPUT_ERROR, f"{name} must contain 1 to 32,000 characters."
            )

    def _redact_optional(self, value: str | None) -> str | None:
        if value is None:
            return None
        return redact_text(value, additional_secrets=self._extra_secrets)


def _validation_messages(error: ValidationError | json.JSONDecodeError) -> list[str]:
    """Extract locations and messages only; never include invalid model data in a repair request."""
    if isinstance(error, json.JSONDecodeError):
        return ["response must be exactly one JSON object"]
    return [
        f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
        for item in error.errors(include_input=False)
    ]
