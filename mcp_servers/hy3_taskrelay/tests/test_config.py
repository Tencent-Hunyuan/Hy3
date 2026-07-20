import pytest

from hy3_taskrelay.config import ConfigError, Settings


def test_missing_api_key_names_the_required_environment_variable() -> None:
    with pytest.raises(ConfigError, match="HY3_API_KEY"):
        Settings.from_env({"HY3_BASE_URL": "https://example.test/v1", "HY3_MODEL": "hy3"})


def test_base_url_must_be_https() -> None:
    with pytest.raises(ConfigError, match=r"HY3_BASE_URL.*https"):
        Settings.from_env(
            {
                "HY3_API_KEY": "test-key",
                "HY3_BASE_URL": "http://example.test/v1",
                "HY3_MODEL": "hy3",
            }
        )


def test_model_must_not_be_blank() -> None:
    with pytest.raises(ConfigError, match="HY3_MODEL"):
        Settings.from_env(
            {
                "HY3_API_KEY": "test-key",
                "HY3_BASE_URL": "https://example.test/v1",
                "HY3_MODEL": "   ",
            }
        )


def test_base_url_requires_a_host_and_forbids_embedded_credentials() -> None:
    with pytest.raises(ConfigError, match=r"HY3_BASE_URL.*host.*credentials"):
        Settings.from_env(
            {
                "HY3_API_KEY": "test-key",
                "HY3_BASE_URL": "https://user:password@/v1",
                "HY3_MODEL": "hy3",
            }
        )


def test_unexpanded_codebuddy_key_placeholder_is_treated_as_missing() -> None:
    with pytest.raises(ConfigError, match="HY3_API_KEY is required"):
        Settings.from_env(
            {
                "HY3_API_KEY": "${HY3_API_KEY}",
                "HY3_BASE_URL": "https://example.test/v1",
                "HY3_MODEL": "hy3",
            }
        )


def test_api_key_has_a_safe_minimum_length_for_exact_redaction() -> None:
    with pytest.raises(ConfigError, match="8 to 4096 printable ASCII"):
        Settings.from_env(
            {
                "HY3_API_KEY": "short",
                "HY3_BASE_URL": "https://example.test/v1",
                "HY3_MODEL": "hy3",
            }
        )


@pytest.mark.parametrize("api_key", ["token-密钥", "test key"])
def test_api_key_must_be_a_printable_ascii_header_token(api_key: str) -> None:
    with pytest.raises(ConfigError, match=r"printable ASCII.*without whitespace"):
        Settings.from_env(
            {
                "HY3_API_KEY": api_key,
                "HY3_BASE_URL": "https://example.test/v1",
                "HY3_MODEL": "hy3",
            }
        )


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("HY3_API_KEY", "key\r\nInjected: value", "printable ASCII"),
        ("HY3_MODEL", "hy3\nInjected", "control bytes"),
    ],
)
def test_header_bound_settings_reject_control_characters(
    name: str, value: str, message: str
) -> None:
    environment = {
        "HY3_API_KEY": "test-key",
        "HY3_BASE_URL": "https://example.test/v1",
        "HY3_MODEL": "hy3",
    }
    environment[name] = value

    with pytest.raises(ConfigError, match=message):
        Settings.from_env(environment)


def test_base_url_rejects_an_invalid_port_without_raw_exception() -> None:
    with pytest.raises(ConfigError, match=r"valid URL.*valid port"):
        Settings.from_env(
            {
                "HY3_API_KEY": "test-key",
                "HY3_BASE_URL": "https://example.test:not-a-port/v1",
                "HY3_MODEL": "hy3",
            }
        )
