from hy3_ci_copilot.security import sanitize_untrusted_text, truncate_middle


def test_terminal_text_is_cleaned_and_secrets_are_redacted() -> None:
    openrouter_key = "sk-or-v1-" + "abcdefghijklmnopqrstuvwxyz"
    aws_key = "AKIA" + "1234567890ABCDEF"
    bearer_token = "abcdefghijkl" + "mnopqrstuvwxyz"
    text = (
        "\x1b[31mERROR\x1b[0m\r\n"
        f"Authorization: Bearer {bearer_token}\n"
        f"OPENROUTER_API_KEY={openrouter_key}\n"
        "clone https://user:password@example.test/repo\n"
        f"AWS_ACCESS_KEY_ID={aws_key}\n"
    )

    cleaned = sanitize_untrusted_text(text)

    assert "\x1b" not in cleaned
    assert "password@example" not in cleaned
    assert "sk-or-v1" not in cleaned
    assert aws_key not in cleaned
    assert cleaned.count("[REDACTED") >= 4


def test_middle_truncation_preserves_failure_tail() -> None:
    text = "A" * 100 + "root cause at the end"

    result = truncate_middle(text, 80, "test log")

    assert len(result) == 80
    assert "omitted from test log" in result
    assert result.endswith("at the end")


def test_truncation_never_exceeds_small_limit() -> None:
    for limit in range(0, 80):
        assert len(truncate_middle("x" * 200, limit, "log")) <= limit


def test_json_yaml_dsn_and_jwt_secrets_are_redacted() -> None:
    jwt = ".".join(("eyJ" + "abcdefghijk", "abcdefghijkl", "abcdefghijkl"))
    text = f"""{{"api_key":"plain-secret-value","access_token":"another-secret"}}
password: |
  multiline-secret
  second-line
DATABASE_URL=postgresql://alice:s3cret@db.example/app
raw {jwt}
"""

    cleaned = sanitize_untrusted_text(text)

    for secret in (
        "plain-secret-value",
        "another-secret",
        "multiline-secret",
        "second-line",
        "s3cret",
        jwt,
    ):
        assert secret not in cleaned
    assert cleaned.count("[REDACTED") >= 4
