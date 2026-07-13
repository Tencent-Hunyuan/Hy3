"""Tests for Repo Scout environment configuration."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from hy3_repo_scout.config import (  # noqa: E402
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    ConfigError,
    Settings,
)


class SettingsTests(unittest.TestCase):
    def test_remote_defaults_require_only_an_api_key(self) -> None:
        settings = Settings.from_env({"HY3_API_KEY": "sk-test"})

        self.assertEqual(settings.api_key, "sk-test")
        self.assertEqual(settings.base_url, DEFAULT_BASE_URL)
        self.assertEqual(settings.model, DEFAULT_MODEL)
        self.assertEqual(settings.reasoning_effort, "high")
        self.assertEqual(settings.max_rounds, 9)
        self.assertEqual(settings.max_tokens, 16_384)
        self.assertNotIn("sk-test", repr(settings))

    def test_api_key_is_required_and_empty_sentinel_is_rejected_for_openrouter(self) -> None:
        with self.assertRaisesRegex(ConfigError, "HY3_API_KEY is required"):
            Settings.from_env({})
        with self.assertRaisesRegex(ConfigError, "real HY3_API_KEY"):
            Settings.from_env({"HY3_API_KEY": "EMPTY"})

    def test_non_openrouter_gateway_can_use_empty_sentinel(self) -> None:
        settings = Settings(
            api_key="EMPTY",
            base_url="https://hy3-gateway.example.com/v1",
        )
        self.assertEqual(settings.api_key, "EMPTY")

    def test_openrouter_key_is_a_supported_fallback(self) -> None:
        settings = Settings.from_env({"OPENROUTER_API_KEY": "or-key"})
        self.assertEqual(settings.api_key, "or-key")

    def test_environment_overrides_are_parsed_and_normalized(self) -> None:
        settings = Settings.from_env(
            {
                "HY3_API_KEY": "  secret  ",
                "HY3_BASE_URL": "http://localhost:8000/v1/",
                "HY3_MODEL": "local-hy3",
                "HY3_TIMEOUT": "12.5",
                "HY3_MAX_ATTEMPTS": "4",
                "HY3_RETRY_BASE_DELAY": "0",
                "HY3_RETRY_MAX_DELAY": "3",
                "HY3_MAX_ROUNDS": "5",
                "HY3_MAX_TOOL_CALLS": "9",
                "HY3_MAX_CONTEXT_CHARS": "1234",
                "HY3_MAX_TOOL_RESULT_CHARS": "321",
                "HY3_MAX_TOKENS": "777",
                "HY3_TEMPERATURE": "0.6",
                "HY3_TOP_P": "0.8",
                "HY3_REASONING_EFFORT": "LOW",
            }
        )

        self.assertEqual(settings.api_key, "secret")
        self.assertEqual(settings.base_url, "http://localhost:8000/v1")
        self.assertEqual(settings.model, "local-hy3")
        self.assertEqual(settings.timeout, 12.5)
        self.assertEqual(settings.max_attempts, 4)
        self.assertEqual(settings.max_rounds, 5)
        self.assertEqual(settings.max_tool_calls, 9)
        self.assertEqual(settings.max_context_chars, 1234)
        self.assertEqual(settings.max_tool_result_chars, 321)
        self.assertEqual(settings.max_tokens, 777)
        self.assertEqual(settings.temperature, 0.6)
        self.assertEqual(settings.top_p, 0.8)
        self.assertEqual(settings.reasoning_effort, "low")

    def test_invalid_numbers_urls_and_reasoning_are_rejected(self) -> None:
        with self.assertRaisesRegex(ConfigError, "HY3_MAX_ROUNDS"):
            Settings.from_env(
                {"HY3_API_KEY": "key", "HY3_MAX_ROUNDS": "not-a-number"}
            )
        with self.assertRaisesRegex(ConfigError, "absolute http"):
            Settings(api_key="key", base_url="localhost:8000/v1")
        with self.assertRaisesRegex(ConfigError, "reasoning_effort"):
            Settings(api_key="key", reasoning_effort="medium")
        with self.assertRaisesRegex(ConfigError, "at least 3"):
            Settings(api_key="key", max_rounds=2)
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value), self.assertRaisesRegex(ConfigError, "finite"):
                Settings(api_key="key", timeout=value)
        with self.assertRaisesRegex(ConfigError, "finite"):
            Settings.from_env({"HY3_API_KEY": "key", "HY3_TIMEOUT": "nan"})
        with self.assertRaisesRegex(ConfigError, "at least 256"):
            Settings(api_key="key", max_tool_result_chars=128)


if __name__ == "__main__":
    unittest.main()
