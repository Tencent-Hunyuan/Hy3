from __future__ import annotations

import sys
import unittest
from pathlib import Path


API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

from common import Hy3Config, reasoning_extra_body


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

        self.assertEqual(
            reasoning_extra_body(self_hosted, "no_think"),
            {"chat_template_kwargs": {"reasoning_effort": "no_think"}},
        )
        self.assertEqual(
            reasoning_extra_body(openrouter, "no_think"),
            {"reasoning": {"effort": "none"}},
        )
        self.assertEqual(
            reasoning_extra_body(openrouter, "high"),
            {"reasoning": {"effort": "high"}},
        )


if __name__ == "__main__":
    unittest.main()
