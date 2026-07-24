from pathlib import Path

import pytest

from hy3_evalforge.errors import ErrorCode, EvalForgeError
from hy3_evalforge.settings import Settings


def test_settings_require_allowed_root() -> None:
    with pytest.raises(EvalForgeError, match="EVALFORGE_ALLOWED_ROOT") as raised:
        Settings.from_environment({})

    assert raised.value.code == ErrorCode.CONFIG_ERROR


def test_settings_hide_key_and_load_extra_secret(tmp_path: Path) -> None:
    settings = Settings.from_environment(
        {
            "EVALFORGE_ALLOWED_ROOT": str(tmp_path),
            "HY3_API_KEY": "test-secret-key",
            "EVALFORGE_REDACT_ENV_VARS": "CUSTOM_SECRET, MISSING",
            "CUSTOM_SECRET": "custom-secret",
        }
    )

    assert "test-secret-key" not in repr(settings)
    assert settings.require_hy3_api_key() == "test-secret-key"
    assert settings.extra_secret_values({"CUSTOM_SECRET": "custom-secret", "MISSING": ""}) == (
        "custom-secret",
    )


def test_settings_reject_invalid_integer(tmp_path: Path) -> None:
    with pytest.raises(EvalForgeError) as raised:
        Settings.from_environment(
            {"EVALFORGE_ALLOWED_ROOT": str(tmp_path), "EVALFORGE_MAX_CASES": "nope"}
        )

    assert raised.value.code == ErrorCode.CONFIG_ERROR


def test_settings_reject_zero_batch_size(tmp_path: Path) -> None:
    with pytest.raises(EvalForgeError) as raised:
        Settings.from_environment(
            {"EVALFORGE_ALLOWED_ROOT": str(tmp_path), "EVALFORGE_BATCH_SIZE": "0"}
        )

    assert raised.value.code == ErrorCode.CONFIG_ERROR
