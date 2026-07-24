import json
from pathlib import Path

import pytest

from hy3_evalforge.core.paths import ArtifactStore
from hy3_evalforge.providers.fake import FakeProvider
from hy3_evalforge.services.run_scorer import RunScorer


def _write_artifacts(root: Path) -> None:
    anchors = {str(score): f"score {score}" for score in range(5)}
    ArtifactStore(root).write_json(
        "eval_spec.json",
        {
            "schema_version": "1.0",
            "spec_id": "spec_0123456789abcdef",
            "goal": "Safe replies.",
            "dimensions": [
                {
                    "name": "safety",
                    "description": "Safe.",
                    "weight": 1,
                    "anchors": anchors,
                }
            ],
            "hard_gates": [],
            "regression_policy": {"practical_delta": 3, "minimum_cases": 1},
            "prompt_version": "judge-v1",
        },
    )
    ArtifactStore(root).write_text(
        "cases.jsonl",
        json.dumps(
            {
                "case_id": "case_0123456789abcdef",
                "input": "hello",
                "expected_behavior": "safe",
                "forbidden_behavior": "INTERNAL_ONLY",
                "dimensions": ["safety"],
                "hard_checks": [
                    {"type": "not_contains", "value": "INTERNAL_ONLY", "severity": "critical"}
                ],
                "tags": ["test"],
                "risk_level": "major",
                "weight": 1,
            }
        )
        + "\n",
    )
    ArtifactStore(root).write_text(
        "responses.jsonl",
        json.dumps(
            {
                "case_id": "case_0123456789abcdef",
                "output": "A safe response.",
                "tool_calls": [],
                "metadata": {},
            }
        )
        + "\n",
    )


@pytest.mark.asyncio
async def test_run_scorer_keeps_critical_rules_separate_from_semantic_score(tmp_path: Path) -> None:
    _write_artifacts(tmp_path)
    judgment = json.dumps(
        {
            "case_id": "case_0123456789abcdef",
            "dimension_scores": {"safety": 4},
            "evidence": [{"dimension": "safety", "quote": "safe", "explanation": "present"}],
        }
    )
    result = await RunScorer(ArtifactStore(tmp_path), FakeProvider([judgment]), max_calls=24).score(
        project_dir=str(tmp_path),
        run_name="baseline",
        responses_path=str(tmp_path / "responses.jsonl"),
        mode="fast",
        allow_expensive=False,
        overwrite=False,
    )

    assert result.run_score == 100
    assert result.critical_failures == 0
    assert (tmp_path / "runs" / "baseline.scorecard.json").is_file()
