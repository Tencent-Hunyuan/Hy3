import pytest
from pydantic import ValidationError

from hy3_evalforge.models.spec import EvaluationDimension, normalize_dimension_weights


def _dimension(name: str, weight: float) -> EvaluationDimension:
    return EvaluationDimension(
        name=name,
        description="Quality dimension.",
        weight=weight,
        anchors={str(score): f"Anchor {score}" for score in range(5)},
    )


def test_weight_normalization_is_deterministic_and_closed() -> None:
    normalized = normalize_dimension_weights(
        [_dimension("correctness", 2), _dimension("safety", 3)]
    )

    assert [item.weight for item in normalized] == [0.4, 0.6]
    assert sum(item.weight for item in normalized) == 1.0


def test_dimension_requires_all_five_anchors() -> None:
    with pytest.raises(ValidationError, match="anchors"):
        EvaluationDimension(
            name="correctness",
            description="Quality dimension.",
            weight=1,
            anchors={"0": "bad"},
        )
