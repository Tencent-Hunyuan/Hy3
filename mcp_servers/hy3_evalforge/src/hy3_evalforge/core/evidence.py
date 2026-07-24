"""Evidence validation for semantic judgments."""

from __future__ import annotations

from hy3_evalforge.errors import ErrorCode, EvalForgeError
from hy3_evalforge.models.judgments import Evidence


def validate_evidence(evidence: list[Evidence], output: str) -> None:
    """Require every non-empty quote to occur verbatim in the candidate output."""
    for item in evidence:
        if item.quote not in output:
            raise EvalForgeError(
                ErrorCode.EVIDENCE_INVALID,
                "A Hy3 evidence quote could not be found verbatim in the candidate output.",
            )
