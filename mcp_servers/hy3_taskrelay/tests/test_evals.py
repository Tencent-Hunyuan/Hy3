from pathlib import Path

import pytest

from evals.run import run_evaluations


@pytest.mark.asyncio
async def test_public_evaluation_bank_has_at_least_ten_independent_passing_cases() -> None:
    project_root = Path(__file__).resolve().parents[1]

    results = await run_evaluations(project_root)

    assert len(results) >= 10
    assert len({result["case_id"] for result in results}) == len(results)
    assert all(result["passed"] for result in results)
