from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from scenarioforge.config import Settings


class SettingsTests(unittest.TestCase):
    def test_defaults_are_tokenhub_hy3(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings.from_env()
        self.assertEqual(settings.model, "hy3")
        self.assertEqual(settings.base_url, "https://tokenhub-intl.tencentcloudmaas.com/v1")
        self.assertFalse(settings.live_ready)
        self.assertFalse(settings.demo_mode)

    def test_demo_mode_is_explicit(self) -> None:
        with patch.dict(os.environ, {"SCENARIOFORGE_DEMO_MODE": "true"}, clear=True):
            self.assertTrue(Settings.from_env().demo_mode)

    def test_rejects_credentials_in_base_url(self) -> None:
        environment = {"HY3_BASE_URL": "https://user:pass@example.test/v1"}
        with (
            patch.dict(os.environ, environment, clear=True),
            self.assertRaisesRegex(ValueError, "credentials"),
        ):
            Settings.from_env()

    def test_rejects_non_positive_timeout(self) -> None:
        with (
            patch.dict(os.environ, {"HY3_TIMEOUT_SECONDS": "0"}, clear=True),
            self.assertRaisesRegex(ValueError, "greater than zero"),
        ):
            Settings.from_env()


if __name__ == "__main__":
    unittest.main()
