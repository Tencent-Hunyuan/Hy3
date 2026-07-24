import json
from pathlib import Path


def test_calibration_fixture_has_balanced_public_reference_pairs() -> None:
    fixture = Path(__file__).parents[1] / "evals" / "calibration_cases.jsonl"
    records = [json.loads(line) for line in fixture.read_text(encoding="utf-8").splitlines()]

    assert len(records) == 30
    assert {item["category"] for item in records} >= {
        "correctness",
        "completeness",
        "constraint_following",
        "safety",
    }
    assert {item["expected_winner"] for item in records} == {"baseline", "candidate", "tie"}
    assert all("sk-" not in item["baseline"] + item["candidate"] for item in records)
