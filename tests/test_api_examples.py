"""Offline tests for deterministic logic in the Hy3 API examples."""

import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from openai import APIStatusError, RateLimitError

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "api" / "examples"
sys.path.insert(0, str(EXAMPLES))


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, EXAMPLES / relative_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {relative_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


common = load_module("hy3_common", "common.py")
tools_example = load_module("hy3_tools", "04_tool_calling/tool_calling.py")
retry_example = load_module(
    "hy3_retry", "06_error_handling_retry/error_handling_retry.py"
)


def status_error(status_code: int, *, retry_after: str | None = None) -> APIStatusError:
    request = httpx.Request("POST", "http://localhost:8000/v1/chat/completions")
    headers = {"retry-after": retry_after} if retry_after else None
    response = httpx.Response(status_code, request=request, headers=headers)
    if status_code == 429:
        return RateLimitError("rate limited", response=response, body=None)
    return APIStatusError("server error", response=response, body=None)


class ConfigurationTests(unittest.TestCase):
    def test_environment_configuration(self) -> None:
        with patch.dict(
            os.environ,
            {
                "HY3_BASE_URL": "http://example.test/v1",
                "HY3_API_KEY": "test-key",
                "HY3_MODEL": "test-model",
            },
        ):
            client = common.create_client()
            self.assertEqual(str(client.base_url), "http://example.test/v1/")
            self.assertEqual(common.model_name(), "test-model")


class ToolCallingTests(unittest.TestCase):
    def test_known_tool(self) -> None:
        result = json.loads(
            tools_example.execute_tool("get_weather", '{"city":"深圳"}')
        )
        self.assertEqual(result["city"], "深圳")
        self.assertEqual(result["temperature_c"], 26)

    def test_unknown_tool_and_invalid_arguments(self) -> None:
        unknown = json.loads(tools_example.execute_tool("delete_all", "{}"))
        invalid = json.loads(tools_example.execute_tool("get_weather", "not-json"))
        self.assertIn("unknown tool", unknown["error"])
        self.assertIn("invalid arguments", invalid["error"])


class RetryTests(unittest.TestCase):
    def test_retry_after_is_honored(self) -> None:
        error = status_error(429, retry_after="3")
        self.assertEqual(retry_example.retry_delay(error, 1), 3.0)

    def test_transient_failure_is_retried(self) -> None:
        attempts = 0
        sleeps: list[float] = []

        def operation():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise status_error(503)
            return "ok"

        with patch.object(retry_example.random, "uniform", return_value=0.0):
            result = retry_example.call_with_retry(operation, sleep=sleeps.append)
        self.assertEqual(result, "ok")
        self.assertEqual(attempts, 2)
        self.assertEqual(sleeps, [1.0])

    def test_client_error_is_not_retried(self) -> None:
        attempts = 0

        def operation():
            nonlocal attempts
            attempts += 1
            raise status_error(400)

        with self.assertRaises(APIStatusError):
            retry_example.call_with_retry(operation, sleep=lambda _: None)
        self.assertEqual(attempts, 1)


if __name__ == "__main__":
    unittest.main()
