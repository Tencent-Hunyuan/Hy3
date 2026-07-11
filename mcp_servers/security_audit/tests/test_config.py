import pydantic
import pytest

from hy3_security_mcp.config import ConfigError, Hy3Config, load_config


def test_defaults_applied_with_only_api_key() -> None:
    config = load_config({"HY3_API_KEY": "sk-test-123"})

    assert config == Hy3Config(
        base_url="https://openrouter.ai/api/v1",
        api_key="sk-test-123",
        model="tencent/hy3:free",
        temperature=0.2,
        max_tokens=8192,
        timeout_seconds=120.0,
    )


def test_all_env_overrides_applied() -> None:
    env = {
        "HY3_BASE_URL": "https://api.hunyuan.cloud.tencent.com/v1",
        "HY3_API_KEY": "sk-override",
        "HY3_MODEL": "hy3",
        "HY3_TEMPERATURE": "0.7",
        "HY3_MAX_TOKENS": "4096",
        "HY3_TIMEOUT_SECONDS": "30.5",
    }

    config = load_config(env)

    assert config == Hy3Config(
        base_url="https://api.hunyuan.cloud.tencent.com/v1",
        api_key="sk-override",
        model="hy3",
        temperature=0.7,
        max_tokens=4096,
        timeout_seconds=30.5,
    )


def test_missing_api_key_raises_config_error_naming_variable_and_env_example() -> None:
    with pytest.raises(ConfigError) as exc_info:
        load_config({})

    message = str(exc_info.value)
    assert "HY3_API_KEY" in message
    assert ".env.example" in message
    assert "OpenRouter" in message
    assert "Tencent Cloud" in message
    assert "local vLLM" in message


def test_empty_api_key_is_rejected() -> None:
    with pytest.raises(ConfigError) as exc_info:
        load_config({"HY3_API_KEY": ""})

    assert "HY3_API_KEY" in str(exc_info.value)


def test_invalid_temperature_raises_config_error_naming_variable_and_value() -> None:
    with pytest.raises(ConfigError) as exc_info:
        load_config({"HY3_API_KEY": "sk-test", "HY3_TEMPERATURE": "abc"})

    message = str(exc_info.value)
    assert "HY3_TEMPERATURE" in message
    assert "abc" in message


def test_invalid_max_tokens_raises_config_error_naming_variable_and_value() -> None:
    with pytest.raises(ConfigError) as exc_info:
        load_config({"HY3_API_KEY": "sk-test", "HY3_MAX_TOKENS": "not-a-number"})

    message = str(exc_info.value)
    assert "HY3_MAX_TOKENS" in message
    assert "not-a-number" in message


def test_config_error_does_not_leak_raw_pydantic_validation_error() -> None:
    with pytest.raises(ConfigError):
        try:
            load_config({"HY3_API_KEY": "sk-test", "HY3_TEMPERATURE": "abc"})
        except pydantic.ValidationError:
            pytest.fail("raw pydantic.ValidationError escaped load_config")
