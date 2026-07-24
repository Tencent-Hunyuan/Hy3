import json
from pathlib import Path

import pytest
from hy3_evalforge.services.spec_designer import SpecDesigner

from hy3_evalforge.core.paths import ArtifactStore
from hy3_evalforge.errors import ErrorCode, EvalForgeError
from hy3_evalforge.providers.fake import FakeProvider


def _valid_spec() -> str:
    return json.dumps(
        {
            "goal": "Answer account questions safely.",
            "dimensions": [
                {
                    "name": "correctness",
                    "description": "Factual accuracy.",
                    "weight": 2,
                    "anchors": {str(score): f"score {score}" for score in range(5)},
                },
                {
                    "name": "safety",
                    "description": "Does not disclose secrets.",
                    "weight": 3,
                    "anchors": {str(score): f"score {score}" for score in range(5)},
                },
            ],
            "hard_gates": [],
        }
    )


@pytest.mark.asyncio
async def test_design_writes_normalized_spec_atomically(tmp_path: Path) -> None:
    designer = SpecDesigner(ArtifactStore(tmp_path), FakeProvider([_valid_spec()]))

    result = await designer.design(
        project_dir=str(tmp_path),
        goal="Help users safely.",
        success_criteria="Give correct answers.",
        failure_examples=None,
        policies=None,
        output_language="en",
        overwrite=False,
    )

    stored = json.loads((tmp_path / "eval_spec.json").read_text(encoding="utf-8"))
    assert result.spec_path == "eval_spec.json"
    assert stored["spec_id"] == result.spec_id
    assert sum(dimension["weight"] for dimension in stored["dimensions"]) == 1.0


@pytest.mark.asyncio
async def test_design_repairs_once_then_fails_closed(tmp_path: Path) -> None:
    designer = SpecDesigner(ArtifactStore(tmp_path), FakeProvider(["not json", "still not json"]))

    with pytest.raises(EvalForgeError) as raised:
        await designer.design(
            project_dir=str(tmp_path),
            goal="Help users safely.",
            success_criteria="Give correct answers.",
            failure_examples=None,
            policies=None,
            output_language="en",
            overwrite=False,
        )

    assert raised.value.code == ErrorCode.HY3_OUTPUT_INVALID
