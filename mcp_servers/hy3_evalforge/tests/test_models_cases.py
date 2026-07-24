import pytest
from pydantic import ValidationError

from hy3_evalforge.models.cases import HardCheck, HardCheckType


def test_hard_check_rejects_executable_or_mismatched_values() -> None:
    with pytest.raises(ValidationError, match="list of strings"):
        HardCheck(type=HardCheckType.CONTAINS_ALL, value="import os")

    with pytest.raises(ValidationError, match="does not accept"):
        HardCheck(type=HardCheckType.VALID_JSON, value="python -c dangerous")


def test_hard_check_accepts_only_declared_dsl_type() -> None:
    with pytest.raises(ValidationError):
        HardCheck.model_validate({"type": "python_expression", "value": "1 + 1"})
