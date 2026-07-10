from __future__ import annotations

import inspect
import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable

import httpx
from openai import APIConnectionError, APITimeoutError, OpenAI


API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

from tests.fake_server import FakeOpenAIServer
from tests.helpers import load_example, run_example


class FakeStatusError(Exception):
    def __init__(self, status_code: int, retry_after: str | None = None) -> None:
        headers = {}
        if retry_after is not None:
            headers["retry-after"] = retry_after
        self.response = SimpleNamespace(
            status_code=status_code,
            headers=headers,
        )
        super().__init__(f"HTTP {status_code}")


def sequence_operation(outcomes: Iterable[Any]) -> Any:
    iterator = iter(outcomes)

    def operation() -> Any:
        outcome = next(iterator)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    return operation


class RetryExampleTests(unittest.TestCase):
    def test_retry_after_header_is_used_before_success(self) -> None:
        module = load_example("06_error_handling_retry.py")
        sleeps: list[float] = []
        operation = sequence_operation(
            [FakeStatusError(429, "2"), "ok"]
        )

        result = module.call_with_retry(operation, sleep=sleeps.append)

        self.assertEqual(result, "ok")
        self.assertEqual(sleeps, [2.0])

    def test_non_finite_retry_after_falls_back_to_full_jitter(self) -> None:
        module = load_example("06_error_handling_retry.py")

        for retry_after in ("inf", "1e309", "nan"):
            with self.subTest(retry_after=retry_after):
                sleeps: list[float] = []
                operation = sequence_operation(
                    [FakeStatusError(429, retry_after), "ok"]
                )

                result = module.call_with_retry(
                    operation,
                    base_delay=0.5,
                    sleep=sleeps.append,
                    random_value=lambda: 0.5,
                )

                self.assertEqual(result, "ok")
                self.assertEqual(sleeps, [0.25])
                self.assertTrue(all(math.isfinite(delay) for delay in sleeps))

    def test_real_sdk_rate_limit_response_is_retried(self) -> None:
        module = load_example("06_error_handling_retry.py")
        completion = {
            "id": "chatcmpl-retry",
            "object": "chat.completion",
            "created": 0,
            "model": "hy3",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "recovered"},
                    "finish_reason": "stop",
                }
            ],
        }
        sleeps: list[float] = []

        with FakeOpenAIServer() as server:
            server.enqueue_json(
                {
                    "error": {
                        "message": "slow down",
                        "type": "rate_limit_error",
                        "code": "rate_limit",
                    }
                },
                status=429,
                headers={"Retry-After": "0"},
            )
            server.enqueue_json(completion)
            with OpenAI(
                base_url=server.base_url,
                api_key="EMPTY",
                max_retries=0,
            ) as client:
                response = module.call_with_retry(
                    lambda: client.chat.completions.create(
                        model="hy3",
                        messages=[{"role": "user", "content": "ping"}],
                    ),
                    sleep=sleeps.append,
                )

        self.assertEqual(response.choices[0].message.content, "recovered")
        self.assertEqual(len(server.requests), 2)
        self.assertEqual(sleeps, [0.0])

    def test_classifies_retryable_transport_and_status_errors(self) -> None:
        module = load_example("06_error_handling_retry.py")
        request = httpx.Request(
            "POST",
            "https://example.invalid/v1/chat/completions",
        )
        retryable = [
            APIConnectionError(request=request),
            APITimeoutError(request),
            *(FakeStatusError(status) for status in (408, 409, 429, 500)),
        ]
        permanent = [FakeStatusError(status) for status in (400, 401, 403, 404)]

        for error in retryable:
            with self.subTest(error=error):
                self.assertTrue(module.is_retryable(error))
        for error in permanent:
            with self.subTest(error=error):
                self.assertFalse(module.is_retryable(error))

    def test_final_attempt_raises_without_another_sleep(self) -> None:
        module = load_example("06_error_handling_retry.py")
        sleeps: list[float] = []
        operation = sequence_operation(
            [FakeStatusError(500), FakeStatusError(500)]
        )

        with self.assertRaises(FakeStatusError):
            module.call_with_retry(
                operation,
                max_attempts=2,
                base_delay=0.5,
                sleep=sleeps.append,
                random_value=lambda: 0.5,
            )

        self.assertEqual(sleeps, [0.25])

    def test_invalid_retry_policy_is_rejected_before_operation(self) -> None:
        module = load_example("06_error_handling_retry.py")
        calls = 0

        def operation() -> str:
            nonlocal calls
            calls += 1
            return "unexpected"

        invalid_policies = (
            ({"max_attempts": 0}, "max_attempts must be at least 1"),
            ({"base_delay": -1}, "base_delay must be non-negative"),
            ({"max_delay": 0}, "max_delay must be positive"),
        )
        for policy, message in invalid_policies:
            with self.subTest(policy=policy):
                with self.assertRaisesRegex(ValueError, f"^{message}$"):
                    module.call_with_retry(operation, **policy)

        self.assertEqual(calls, 0)

    def test_simulation_needs_no_api_configuration(self) -> None:
        module = load_example("06_error_handling_retry.py")
        result = run_example(
            "06_error_handling_retry.py",
            "--simulate",
            extra_env={
                "HY3_BACKEND": "",
                "HY3_BASE_URL": "",
                "HY3_API_KEY": "",
                "HY3_MODEL": "",
                "HY3_TIMEOUT": "",
            },
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            [
                "Retry 2/4 in 0.00s after RateLimitError",
                "rate_limit: recovered",
                "Retry 2/4 in 0.00s after APITimeoutError",
                "timeout: recovered",
                "Retry 2/4 in 0.00s after APIConnectionError",
                "connection: recovered",
            ],
        )
        self.assertIn(
            "create_client(config, max_retries=0)",
            inspect.getsource(module.main),
        )


if __name__ == "__main__":
    unittest.main()
