"""Run the synthetic regression example only when real Hy3 credentials are available."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from hy3_evalforge.core.paths import ArtifactStore
from hy3_evalforge.providers.hy3 import Hy3Provider
from hy3_evalforge.services.run_comparator import RunComparator
from hy3_evalforge.services.run_scorer import RunScorer
from hy3_evalforge.settings import Settings


async def main() -> None:
    if not os.environ.get("HY3_API_KEY"):
        raise SystemExit("HY3_API_KEY is not configured; live validation was not run.")
    root = Path(__file__).parents[1]
    example = root / "examples" / "support_agent_regression"
    settings = Settings.from_environment({**os.environ, "EVALFORGE_ALLOWED_ROOT": str(example)})
    scorer = RunScorer(
        ArtifactStore(example),
        Hy3Provider(settings),
        max_calls=settings.max_model_calls,
        extra_secrets=settings.extra_secret_values(),
    )
    for run_name in ("baseline", "candidate"):
        await scorer.score(
            project_dir=str(example),
            run_name=run_name,
            responses_path=str(example / f"{run_name}.jsonl"),
            mode="fast",
            allow_expensive=False,
            overwrite=True,
        )
    comparison = await RunComparator(
        ArtifactStore(example),
        Hy3Provider(settings),
        max_calls=settings.max_model_calls,
        extra_secrets=settings.extra_secret_values(),
    ).compare_with_pairwise(
        project_dir=str(example),
        baseline_run="baseline",
        candidate_run="candidate",
        mode="rigorous",
        practical_delta=3,
        allow_expensive=False,
        overwrite=True,
    )
    print(f"Real Hy3 comparison complete: {comparison.status.value}; {comparison.report_path}")


if __name__ == "__main__":
    asyncio.run(main())
