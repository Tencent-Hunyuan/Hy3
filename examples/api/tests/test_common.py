from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

import common
from common import Hy3Config, create_client, reasoning_extra_body


class Hy3ConfigTests(unittest.TestCase):
    def test_defaults(self) -> None:
        config = Hy3Config.from_mapping({})

        self.assertEqual(config.backend, "self_hosted")
        self.assertEqual(config.base_url, "http://127.0.0.1:8000/v1")
        self.assertEqual(config.api_key, "EMPTY")
        self.assertEqual(config.model, "hy3")
        self.assertEqual(config.timeout, 120.0)

    def test_openrouter_rejects_empty_api_key(self) -> None:
        with self.assertRaisesRegex(ValueError, "HY3_API_KEY"):
            Hy3Config.from_mapping({"HY3_BACKEND": "openrouter", "HY3_API_KEY": "EMPTY"})

    def test_openrouter_defaults(self) -> None:
        config = Hy3Config.from_mapping(
            {"HY3_BACKEND": "openrouter", "HY3_API_KEY": "test-key"}
        )

        self.assertEqual(config.base_url, "https://openrouter.ai/api/v1")
        self.assertEqual(config.model, "tencent/hy3:free")

    def test_empty_string_settings_are_rejected(self) -> None:
        for variable in ("HY3_BASE_URL", "HY3_API_KEY", "HY3_MODEL"):
            with self.subTest(variable=variable):
                with self.assertRaisesRegex(ValueError, variable):
                    Hy3Config.from_mapping({variable: ""})

    def test_non_string_settings_are_rejected(self) -> None:
        for variable in ("HY3_BASE_URL", "HY3_API_KEY", "HY3_MODEL"):
            for value in (None, 123):
                with self.subTest(variable=variable, value=value):
                    with self.assertRaisesRegex(ValueError, variable):
                        Hy3Config.from_mapping({variable: value})

    def test_repr_redacts_api_key(self) -> None:
        secret = "sample-secret"
        config = Hy3Config.from_mapping({"HY3_API_KEY": secret})

        self.assertNotIn(secret, repr(config))

    def test_invalid_backend_and_timeouts_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "HY3_BACKEND"):
            Hy3Config.from_mapping({"HY3_BACKEND": "auto"})

        for timeout in ("0", "-1", "nan", "inf", "not-a-number"):
            with self.subTest(timeout=timeout):
                with self.assertRaisesRegex(ValueError, "HY3_TIMEOUT"):
                    Hy3Config.from_mapping({"HY3_TIMEOUT": timeout})

    def test_reasoning_mapping(self) -> None:
        self_hosted = Hy3Config.from_mapping({})
        openrouter = Hy3Config.from_mapping(
            {"HY3_BACKEND": "openrouter", "HY3_API_KEY": "test-key"}
        )

        for effort in ("no_think", "low", "high"):
            with self.subTest(backend="self_hosted", effort=effort):
                self.assertEqual(
                    reasoning_extra_body(self_hosted, effort),
                    {"chat_template_kwargs": {"reasoning_effort": effort}},
                )

        for effort, mapped_effort in (
            ("no_think", "none"),
            ("low", "low"),
            ("high", "high"),
        ):
            with self.subTest(backend="openrouter", effort=effort):
                self.assertEqual(
                    reasoning_extra_body(openrouter, effort),
                    {"reasoning": {"effort": mapped_effort}},
                )

    def test_invalid_reasoning_effort_is_rejected(self) -> None:
        config = Hy3Config.from_mapping({})

        with self.assertRaises(ValueError):
            reasoning_extra_body(config, "medium")

    def test_from_env_loads_dotenv_without_overriding_environment(self) -> None:
        environment = {
            "HY3_BACKEND": "self_hosted",
            "HY3_BASE_URL": "https://environment.example/v1",
            "HY3_API_KEY": "environment-key",
            "HY3_MODEL": "environment-model",
            "HY3_TIMEOUT": "45",
        }

        with patch.dict(os.environ, environment, clear=True):
            with patch("common.load_dotenv") as load_dotenv:
                config = Hy3Config.from_env()

        load_dotenv.assert_called_once_with(common.API_DIR / ".env", override=False)
        self.assertEqual(config.base_url, environment["HY3_BASE_URL"])
        self.assertEqual(config.api_key, environment["HY3_API_KEY"])
        self.assertEqual(config.model, environment["HY3_MODEL"])
        self.assertEqual(config.timeout, 45.0)

    def test_create_client_forwards_configuration(self) -> None:
        config = Hy3Config.from_mapping(
            {
                "HY3_BASE_URL": "https://example.test/v1",
                "HY3_API_KEY": "test-key",
                "HY3_TIMEOUT": "30",
            }
        )

        with patch("common.OpenAI") as openai:
            client = create_client(config, max_retries=7)

        self.assertIs(client, openai.return_value)
        openai.assert_called_once_with(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=config.timeout,
            max_retries=7,
        )


if __name__ == "__main__":
    unittest.main()
