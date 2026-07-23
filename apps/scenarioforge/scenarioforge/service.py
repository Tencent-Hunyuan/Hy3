"""Orchestrates Hy3 analysis, validation, and transparent metadata."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Protocol

from .models import RehearsalRequest, validate_analysis, validate_decision
from .prompts import ANALYSIS_SYSTEM, DECISION_SYSTEM


class JsonCompleter(Protocol):
    def complete_json(
        self, *, system: str, user: str, max_tokens: int = 2_800
    ) -> tuple[dict[str, Any], dict[str, Any]]: ...


class RehearsalService:
    def __init__(self, client: JsonCompleter) -> None:
        self.client = client

    def run(self, request: RehearsalRequest) -> dict[str, Any]:
        source = json.dumps(request.as_prompt_payload(), ensure_ascii=False, indent=2)
        analysis_raw, first_meta = self.client.complete_json(
            system=ANALYSIS_SYSTEM,
            user=f"<user_plan>\n{source}\n</user_plan>",
        )
        analysis = validate_analysis(analysis_raw)

        decision_input = json.dumps(
            {"user_plan": request.as_prompt_payload(), "validated_analysis": analysis},
            ensure_ascii=False,
            indent=2,
        )
        decision_raw, second_meta = self.client.complete_json(
            system=DECISION_SYSTEM,
            user=f"<rehearsal_context>\n{decision_input}\n</rehearsal_context>",
            max_tokens=2_000,
        )
        decision = validate_decision(decision_raw)

        digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:12]
        return {
            "mode": "live",
            "input_digest": digest,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "analysis": analysis,
            "decision": decision,
            "provider": {
                "name": "Hy3",
                "model": second_meta.get("model") or first_meta.get("model"),
                "calls": 2,
                "request_ids": [
                    item
                    for item in (first_meta.get("request_id"), second_meta.get("request_id"))
                    if item
                ],
                "usage": _merge_usage(first_meta.get("usage"), second_meta.get("usage")),
            },
        }


def _merge_usage(first: Any, second: Any) -> dict[str, int]:
    result: dict[str, int] = {}
    for source in (first, second):
        if not isinstance(source, dict):
            continue
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            value = source.get(key)
            if isinstance(value, int):
                result[key] = result.get(key, 0) + value
    return result
