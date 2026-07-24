import json
from pathlib import Path

import pytest

from hy3_evalforge.core.paths import ArtifactStore
from hy3_evalforge.errors import ErrorCode, EvalForgeError
from hy3_evalforge.models.reports import ComparisonStatus
from hy3_evalforge.providers.fake import FakeProvider
from hy3_evalforge.services.run_comparator import RunComparator, _map_winner


def _scorecard(score: float, critical: bool) -> dict[str, object]:
    return {
        "spec_id": "spec_0123456789abcdef",
        "entries": [
            {
                "case_id": f"case_{index:016x}",
                "semantic": {"semantic_score": score},
                "hard_checks": [
                    {
                        "check_type": "not_contains",
                        "passed": not critical or index != 0,
                        "severity": "critical",
                    }
                ],
            }
            for index in range(10)
        ],
    }


def test_comparator_blocks_new_critical_failure(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    (tmp_path / "runs").mkdir()
    store.write_json("runs/baseline.scorecard.json", _scorecard(60, False))
    store.write_json("runs/candidate.scorecard.json", _scorecard(90, True))

    result = RunComparator(store).compare(
        project_dir=str(tmp_path),
        baseline_run="baseline",
        candidate_run="candidate",
        practical_delta=3,
        overwrite=False,
    )

    assert result.status is ComparisonStatus.BLOCKED
    report = json.loads((tmp_path / result.json_path).read_text(encoding="utf-8"))
    assert report["new_critical_failures"] == 1


def test_comparator_marks_small_sample_inconclusive(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    (tmp_path / "runs").mkdir()
    baseline = _scorecard(60, False)
    candidate = _scorecard(90, False)
    baseline["entries"] = baseline["entries"][:2]
    candidate["entries"] = candidate["entries"][:2]
    store.write_json("runs/baseline.scorecard.json", baseline)
    store.write_json("runs/candidate.scorecard.json", candidate)

    result = RunComparator(store).compare(
        project_dir=str(tmp_path),
        baseline_run="baseline",
        candidate_run="candidate",
        practical_delta=3,
        overwrite=False,
    )

    assert result.status is ComparisonStatus.INCONCLUSIVE


def test_pairwise_winner_mapping_hides_real_run_names() -> None:
    assert _map_winner("A", False) == "baseline"
    assert _map_winner("B", False) == "candidate"
    assert _map_winner("A", True) == "candidate"
    assert _map_winner("B", True) == "baseline"
    assert _map_winner("TIE", True) == "tie"


def _pairwise_artifacts(root: Path) -> None:
    store = ArtifactStore(root)
    (root / "runs").mkdir()
    case_id = "case_0123456789abcdef"
    store.write_text(
        "cases.jsonl",
        json.dumps(
            {
                "case_id": case_id,
                "input": "hello",
                "expected_behavior": "safe",
                "forbidden_behavior": "none",
                "dimensions": ["safety"],
                "hard_checks": [],
                "tags": ["test"],
                "risk_level": "major",
                "weight": 1,
            }
        )
        + "\n",
    )
    store.write_text(
        "baseline.jsonl",
        json.dumps({"case_id": case_id, "output": "baseline safe", "tool_calls": []}) + "\n",
    )
    store.write_text(
        "candidate.jsonl",
        json.dumps(
            {
                "case_id": case_id,
                "output": "candidate api_key=ultra-secret-token-value",
                "tool_calls": [],
            }
        )
        + "\n",
    )
    baseline = _scorecard(60, False)
    candidate = _scorecard(80, False)
    baseline["entries"] = baseline["entries"][:1]
    candidate["entries"] = candidate["entries"][:1]
    baseline["responses_path"] = str(root / "baseline.jsonl")
    candidate["responses_path"] = str(root / "candidate.jsonl")
    store.write_json("runs/baseline.scorecard.json", baseline)
    store.write_json("runs/candidate.scorecard.json", candidate)


@pytest.mark.asyncio
async def test_pairwise_comparison_redacts_and_repairs_once(tmp_path: Path) -> None:
    _pairwise_artifacts(tmp_path)
    provider = FakeProvider(
        ["not json", json.dumps({"winner": "A", "evidence": [{"quote": "baseline safe"}]})],
        record_requests=True,
    )

    result = await RunComparator(ArtifactStore(tmp_path), provider).compare_with_pairwise(
        project_dir=str(tmp_path),
        baseline_run="baseline",
        candidate_run="candidate",
        mode="rigorous",
        practical_delta=3,
        allow_expensive=False,
        overwrite=False,
    )

    assert provider.request_count == 2
    assert "ultra-secret-token-value" not in provider.requests[0].user_prompt
    assert "[REDACTED_SECRET]" in provider.requests[0].user_prompt
    report = json.loads((tmp_path / result.json_path).read_text(encoding="utf-8"))
    assert report["pairwise"]["judgments"][0]["evidence"] == [{"quote": "baseline safe"}]


@pytest.mark.asyncio
async def test_pairwise_budget_requires_explicit_override(tmp_path: Path) -> None:
    _pairwise_artifacts(tmp_path)

    with pytest.raises(EvalForgeError) as raised:
        await RunComparator(
            ArtifactStore(tmp_path), FakeProvider([]), max_calls=0
        ).compare_with_pairwise(
            project_dir=str(tmp_path),
            baseline_run="baseline",
            candidate_run="candidate",
            mode="fast",
            practical_delta=3,
            allow_expensive=False,
            overwrite=False,
        )

    assert raised.value.code is ErrorCode.BUDGET_EXCEEDED
