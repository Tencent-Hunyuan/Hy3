from __future__ import annotations

import pytest

from common import ApiConfig, ConfigError, normalize_base_url, thinking_body


def test_missing_api_key_is_rejected() -> None:
    with pytest.raises(ConfigError, match="HY3_API_KEY"):
        ApiConfig.from_env({"HY3_BASE_URL": "https://tokenhub.tencentmaas.com/v1"})


def test_missing_base_url_is_rejected() -> None:
    with pytest.raises(ConfigError, match="HY3_BASE_URL"):
        ApiConfig.from_env({"HY3_API_KEY": "local-test-placeholder"})


@pytest.mark.parametrize("placeholder", ["", "EMPTY", "YOUR_API_KEY", "replace_me"])
def test_key_placeholders_are_rejected(placeholder: str) -> None:
    with pytest.raises(ConfigError):
        ApiConfig.from_env(
            {
                "HY3_API_KEY": placeholder,
                "HY3_BASE_URL": "https://tokenhub.tencentmaas.com/v1",
            }
        )


def test_documented_base_urls_are_normalized() -> None:
    assert (
        normalize_base_url("https://tokenhub.tencentmaas.com/v1/")
        == "https://tokenhub.tencentmaas.com/v1"
    )
    assert (
        normalize_base_url("https://api.lkeap.cloud.tencent.com/plan/v3/")
        == "https://api.lkeap.cloud.tencent.com/plan/v3"
    )


@pytest.mark.parametrize(
    "url",
    [
        "tokenhub.tencentmaas.com/v1",
        "http://tokenhub.tencentmaas.com/v1",
        "https://user:password@tokenhub.tencentmaas.com/v1",
        "https://tokenhub.tencentmaas.com/v1/chat/completions",
        "https://tokenhub.tencentmaas.com/v1?key=value",
    ],
)
def test_unsafe_or_resource_urls_are_rejected(url: str) -> None:
    with pytest.raises(ConfigError):
        normalize_base_url(url)


def test_local_http_base_url_is_allowed_for_explicit_local_testing() -> None:
    assert normalize_base_url("http://127.0.0.1:8000/v1/") == "http://127.0.0.1:8000/v1"


def test_config_uses_hy3_default_model() -> None:
    config = ApiConfig.from_env(
        {
            "HY3_API_KEY": "local-test-placeholder",
            "HY3_BASE_URL": "https://tokenhub.tencentmaas.com/v1",
        }
    )
    assert config.model == "hy3"


def test_invalid_model_is_rejected() -> None:
    with pytest.raises(ConfigError, match="HY3_MODEL"):
        ApiConfig.from_env(
            {
                "HY3_API_KEY": "local-test-placeholder",
                "HY3_BASE_URL": "https://tokenhub.tencentmaas.com/v1",
                "HY3_MODEL": "not a model",
            }
        )


def test_thinking_body_uses_hosted_top_level_fields() -> None:
    assert thinking_body(False) == {"thinking": {"type": "disabled"}}
    assert thinking_body(True, "medium") == {
        "thinking": {"type": "enabled"},
        "reasoning_effort": "medium",
    }
    with pytest.raises(ValueError):
        thinking_body(False, "low")
    with pytest.raises(ValueError):
        thinking_body(True, "no_think")
