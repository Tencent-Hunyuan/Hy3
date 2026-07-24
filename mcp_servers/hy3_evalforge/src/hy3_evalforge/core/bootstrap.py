"""Deterministic bootstrap confidence intervals for run comparisons."""

from __future__ import annotations

import random


def mean_difference_interval(
    differences: list[float], *, seed: int, samples: int = 2_000
) -> tuple[float, float]:
    """Return the 2.5% and 97.5% bootstrap quantiles with a fixed seed."""
    if not differences:
        raise ValueError("at least one difference is required")
    generator = random.Random(seed)
    size = len(differences)
    means = sorted(
        sum(generator.choice(differences) for _ in range(size)) / size for _ in range(samples)
    )
    return means[int(samples * 0.025)], means[int(samples * 0.975)]
