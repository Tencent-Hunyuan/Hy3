from __future__ import annotations

from types import SimpleNamespace

from common import redact_data, response_summary, safe_error_message


def test_redaction_removes_headers_keys_and_known_secrets() -> None:
    secret = "local-test-secret-value"
    value = {
        "Authorization": f"Bearer {secret}",
        "nested": {"api-key": secret, "text": f"prefix {secret} suffix"},
        "usage": {"total_tokens": 12},
    }
    redacted = redact_data(value, secrets=[secret])
    rendered = str(redacted)
    assert secret not in rendered
    assert redacted["usage"]["total_tokens"] == 12
    assert redacted["Authorization"] == "***REDACTED***"


def test_response_summary_omits_request_id() -> None:
    message = SimpleNamespace(
        role="assistant",
        reasoning_content="reasoning",
        content="answer",
        tool_calls=None,
    )
    response = SimpleNamespace(
        id="request-id-must-not-be-printed",
        model="hy3",
        choices=[SimpleNamespace(message=message, finish_reason="stop")],
        usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3),
    )
    summary = response_summary(response)
    assert "request-id-must-not-be-printed" not in str(summary)
    assert summary["message"]["reasoning_content"] == "reasoning"


def test_safe_error_message_omits_exception_body_and_request_id() -> None:
    class UnsafeApiError(Exception):
        status_code = 401

    error = UnsafeApiError("secret body; request_id=req-sensitive")
    message = safe_error_message(error)
    assert "HTTP 401" in message
    assert "secret body" not in message
    assert "req-sensitive" not in message
