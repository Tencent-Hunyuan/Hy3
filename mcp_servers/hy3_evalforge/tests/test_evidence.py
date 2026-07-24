import pytest

from hy3_evalforge.core.evidence import validate_evidence
from hy3_evalforge.errors import ErrorCode, EvalForgeError
from hy3_evalforge.models.judgments import Evidence


def test_evidence_requires_verbatim_quote() -> None:
    validate_evidence(
        [Evidence(dimension="safety", quote="safe", explanation="present")], "safe reply"
    )
    with pytest.raises(EvalForgeError) as raised:
        validate_evidence(
            [Evidence(dimension="safety", quote="missing", explanation="no")], "safe reply"
        )
    assert raised.value.code == ErrorCode.EVIDENCE_INVALID
