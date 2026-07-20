import json
import time

import pytest

from hy3_taskrelay.security import REDACTED, redact_data, redact_text


@pytest.mark.parametrize(
    ("value", "secret"),
    [
        ('{"api_key": "json-secret-123456"}', "json-secret-123456"),
        ("{'access_token': 'mapping-secret-123456'}", "mapping-secret-123456"),
        ('"password" = "quoted-secret-123456"', "quoted-secret-123456"),
        ('{"authorization": "Bearer auth-secret-123456"}', "auth-secret-123456"),
        ("Authorization: Token auth-secret-123456", "auth-secret-123456"),
        ("Authorization: ApiKey auth-secret-123456", "auth-secret-123456"),
        (
            "Authorization: Digest username=demo, nonce=nonce-secret-123456, "
            "response=response-secret-123456",
            "nonce-secret-123456",
        ),
        ('{"cookie": "session=cookie-secret-123456"}', "cookie-secret-123456"),
        ("client_secret=client-secret-123456", "client-secret-123456"),
        ("refresh_token=refresh-secret-123456", "refresh-secret-123456"),
        ("AWS_SECRET_ACCESS_KEY=aws-secret-123456", "aws-secret-123456"),
        ("private_key=private-secret-123456", "private-secret-123456"),
        ("AWS_SESSION_TOKEN=aws-session-secret-123456", "aws-session-secret-123456"),
        ("GITHUB_TOKEN=github-secret-123456", "github-secret-123456"),
        ("SLACK_BOT_TOKEN=slack-secret-123456", "slack-secret-123456"),
        ("ID_TOKEN=id-secret-123456", "id-secret-123456"),
        ("OPENAI_API_KEY=openai-secret-123456", "openai-secret-123456"),
        ("ANTHROPIC_API_KEY=anthropic-secret-123456", "anthropic-secret-123456"),
        ("MY_PRIVATE_KEY=private-secret-123456", "private-secret-123456"),
        ("accessToken=access-secret-123456", "access-secret-123456"),
        ("refreshToken=refresh-secret-123456", "refresh-secret-123456"),
        ("clientSecret=client-secret-123456", "client-secret-123456"),
        ("sessionToken=session-secret-123456", "session-secret-123456"),
        (
            "DefaultEndpointsProtocol=https;AccountName=demo;"
            "AccountKey=azure-secret-123456;EndpointSuffix=core.windows.net",
            "azure-secret-123456",
        ),
        (
            "SharedAccessSignature=sv=1&sig=shared-secret-123456",
            "shared-secret-123456",
        ),
        (
            "connection_string=Server=db;Password=connection-secret-123456",
            "connection-secret-123456",
        ),
    ],
)
def test_redact_text_handles_quoted_structured_credential_keys(value: str, secret: str) -> None:
    redacted = redact_text(value)

    assert secret not in redacted
    assert REDACTED in redacted


def test_redact_text_preserves_json_string_shape() -> None:
    value = json.dumps(
        {
            "api_key": "json-secret-123456",
            "authorization": "Bearer auth-secret-123456",
            "cookie": "session=cookie-secret-123456",
        }
    )

    redacted = json.loads(redact_text(value))

    assert redacted == {
        "api_key": REDACTED,
        "authorization": REDACTED,
        "cookie": REDACTED,
    }


def test_redact_data_preserves_identifiers_while_redacting_free_text() -> None:
    identifier = "ev_sk-abcdefgh"

    redacted = redact_data(
        {
            "evidence_id": identifier,
            "evidence_ids": [identifier],
            "text": "Observed sk-abcdefgh in a log.",
        }
    )

    assert redacted["evidence_id"] == identifier
    assert redacted["evidence_ids"] == [identifier]
    assert redacted["text"] == f"Observed {REDACTED} in a log."


@pytest.mark.parametrize(
    "credential",
    [
        "https://demo-user:demo-password@example.test/path",
        "amqp://demo-user:demo-password@broker.test/vhost",
        "redis://:demo-password@cache.test/0",
        "eyJabcdefghijk.abcdefghijkl.abcdefghijkl",
        "ghp_abcdefghijklmnopqrstuvwxyz123456",
        "AKIAABCDEFGHIJKLMNOP",
        "AKIDabcdefghijklmnopqrstuvwx",
    ],
)
def test_common_standalone_credentials_are_redacted(credential: str) -> None:
    redacted = redact_text(f"observed {credential}")

    assert credential not in redacted
    assert REDACTED in redacted


def test_non_sensitive_hyphenated_input_is_processed_in_bounded_time() -> None:
    value = ("ordinary-") * 6_000 + "field=value"

    started = time.perf_counter()
    redacted = redact_text(value)
    elapsed = time.perf_counter() - started

    assert redacted == value
    assert elapsed < 1.0
