from hy3_evalforge.errors import ErrorCode, EvalForgeError


def test_error_payload_redacts_sensitive_and_complex_diagnostics() -> None:
    error = EvalForgeError(
        ErrorCode.PROVIDER_ERROR,
        "Provider request failed.",
        details={
            "request_key": "should-not-leak",
            "response_body": "provider output",
            "attempt": 2,
            "context": "Bearer abcdefghijklmnop",
            "nested": {"untrusted": "data"},
        },
    )

    assert error.to_payload() == {
        "error": {
            "code": "PROVIDER_ERROR",
            "message": "Provider request failed.",
            "details": {
                "request_key": "[REDACTED]",
                "response_body": "[REDACTED]",
                "attempt": 2,
                "context": "[REDACTED_SECRET]",
                "nested": "[OMITTED]",
            },
        }
    }
