"""Deterministic semantic-score and judge-agreement aggregation."""

from __future__ import annotations

from collections import Counter
from statistics import median

from hy3_evalforge.models.judgments import SingleJudgment
from hy3_evalforge.models.spec import EvaluationDimension


def aggregate_scores(
    judgments: list[SingleJudgment], dimensions: list[EvaluationDimension]
) -> dict[str, float]:
    """Use per-dimension medians and the frozen 25 × weighted-score formula."""
    by_dimension = {dimension.name: [] for dimension in dimensions}
    for judgment in judgments:
        for name in by_dimension:
            by_dimension[name].append(judgment.dimension_scores[name])
    medians = {name: float(median(scores)) for name, scores in by_dimension.items()}
    weights = {dimension.name: dimension.weight for dimension in dimensions}
    semantic_score = 25 * sum(weights[name] * score for name, score in medians.items())
    return {"semantic_score": semantic_score, "agreement": agreement(judgments), **medians}


def agreement(judgments: list[SingleJudgment]) -> float:
    """Return the fraction represented by the most common complete score conclusion."""
    if not judgments:
        return 0.0
    conclusions = [tuple(sorted(item.dimension_scores.items())) for item in judgments]
    return Counter(conclusions).most_common(1)[0][1] / len(conclusions)
