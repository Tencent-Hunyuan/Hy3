"""Run the public pairwise calibration fixture against Hy3 when explicitly authorized."""

from __future__ import annotations

import asyncio
import json
import os
import random
from pathlib import Path

from hy3_evalforge.core.paths import ArtifactStore
from hy3_evalforge.core.redaction import redact_text
from hy3_evalforge.models.cases import EvalCase
from hy3_evalforge.prompts.compare_runs import build_request
from hy3_evalforge.providers.hy3 import Hy3Provider
from hy3_evalforge.services.run_comparator import RunComparator, _map_winner
from hy3_evalforge.settings import Settings


async def main() -> None:
    if not os.environ.get("HY3_API_KEY"):
        raise SystemExit("HY3_API_KEY is not configured; calibration was not run.")
    root = Path(__file__).parents[1]
    records = [
        json.loads(line)
        for line in (root / "evals" / "calibration_cases.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    settings = Settings.from_environment({**os.environ, "EVALFORGE_ALLOWED_ROOT": str(root)})
    if (
        len(records) > settings.max_model_calls
        and os.environ.get("EVALFORGE_ALLOW_EXPENSIVE") != "1"
    ):
        raise SystemExit(
            "Calibration needs 30 model calls. Set EVALFORGE_ALLOW_EXPENSIVE=1 to authorize it."
        )

    store = ArtifactStore(root)
    comparator = RunComparator(
        store,
        Hy3Provider(settings),
        max_calls=settings.max_model_calls,
        extra_secrets=settings.extra_secret_values(),
    )
    generator = random.Random(0)
    results = []
    for index, record in enumerate(records):
        case = EvalCase.model_validate(
            {
                "case_id": f"case_{index:016x}",
                "input": record["input"],
                "expected_behavior": "Give a safe and useful customer-support response.",
                "forbidden_behavior": "Do not reveal sensitive information or ignore constraints.",
                "dimensions": [record["category"]],
                "hard_checks": [],
                "tags": ["calibration"],
                "risk_level": "major",
                "weight": 1,
            }
        )
        swapped = generator.choice([False, True])
        first = record["candidate"] if swapped else record["baseline"]
        second = record["baseline"] if swapped else record["candidate"]
        judgment = await comparator._judge_pairwise(
            build_request(
                case,
                redact_text(first, additional_secrets=settings.extra_secret_values()),
                redact_text(second, additional_secrets=settings.extra_secret_values()),
                "high",
            ),
            redact_text(first, additional_secrets=settings.extra_secret_values()),
            redact_text(second, additional_secrets=settings.extra_secret_values()),
        )
        actual = _map_winner(judgment.winner, swapped)
        results.append(
            {
                "id": record["id"],
                "expected_winner": record["expected_winner"],
                "actual_winner": actual,
                "correct": actual == record["expected_winner"],
            }
        )

    accuracy = sum(item["correct"] for item in results) / len(results)
    store.write_json(
        "evals/calibration_results.json",
        {"case_count": len(results), "pairwise_accuracy": accuracy, "results": results},
        overwrite=True,
    )
    print(f"Calibration complete: {accuracy:.1%}; evals/calibration_results.json")


if __name__ == "__main__":
    asyncio.run(main())
