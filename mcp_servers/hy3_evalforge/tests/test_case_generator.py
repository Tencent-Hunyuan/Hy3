import json
from pathlib import Path

import pytest

from hy3_evalforge.core.paths import ArtifactStore
from hy3_evalforge.errors import ErrorCode, EvalForgeError
from hy3_evalforge.providers.fake import FakeProvider
from hy3_evalforge.services.case_generator import CaseGenerator


def _spec() -> dict[str, object]:
    anchors = {str(score): f"score {score}" for score in range(5)}
    return {
        "schema_version": "1.0",
        "spec_id": "spec_0123456789abcdef",
        "goal": "Help safely.",
        "dimensions": [
            {"name": "correctness", "description": "Correct.", "weight": 0.5, "anchors": anchors},
            {"name": "safety", "description": "Safe.", "weight": 0.5, "anchors": anchors},
        ],
        "hard_gates": [],
        "regression_policy": {"practical_delta": 3, "minimum_cases": 4},
        "prompt_version": "judge-v1",
    }


def _cases() -> str:
    return json.dumps(
        {
            "cases": [
                {
                    "input": f"case {index}",
                    "expected_behavior": "Answer safely.",
                    "forbidden_behavior": "Leak a secret.",
                    "dimensions": ["correctness"] if index % 2 else ["safety"],
                    "hard_checks": [],
                    "tags": ["boundary"],
                    "risk_level": "major",
                    "weight": 1,
                }
                for index in range(4)
            ]
        }
    )


@pytest.mark.asyncio
async def test_generator_writes_unique_covered_jsonl(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    store.write_json("eval_spec.json", _spec())
    result = await CaseGenerator(store, FakeProvider([_cases()])).generate(
        project_dir=str(tmp_path), categories="boundary", count=4, seed=7, overwrite=False
    )

    lines = (tmp_path / "cases.jsonl").read_text(encoding="utf-8").splitlines()
    assert result.case_count == 4
    assert len(lines) == 4
    assert not json.loads((tmp_path / "case_coverage.json").read_text())["uncovered_dimensions"]


@pytest.mark.asyncio
async def test_generator_rejects_near_duplicate_inputs(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    store.write_json("eval_spec.json", _spec())
    duplicate = json.loads(_cases())
    duplicate["cases"][1]["input"] = "case 0"
    generator = CaseGenerator(store, FakeProvider([json.dumps(duplicate), json.dumps(duplicate)]))

    with pytest.raises(EvalForgeError) as raised:
        await generator.generate(
            project_dir=str(tmp_path), categories="boundary", count=4, seed=7, overwrite=False
        )

    assert raised.value.code == ErrorCode.HY3_OUTPUT_INVALID
