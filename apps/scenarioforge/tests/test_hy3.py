from __future__ import annotations

import io
import json
import unittest
import urllib.error
from typing import Any

from scenarioforge.config import Settings
from scenarioforge.hy3 import Hy3Client, Hy3Error


def settings() -> Settings:
    return Settings(
        base_url="https://hy3.example.test/v1",
        api_key="test-secret",
        model="hy3",
        timeout_seconds=3,
        demo_mode=False,
    )


class Hy3ClientTests(unittest.TestCase):
    def test_sends_openai_compatible_json_request(self) -> None:
        captured: dict[str, Any] = {}

        def transport(request: Any, timeout: float) -> dict[str, Any]:
            captured["url"] = request.full_url
            captured["auth"] = request.get_header("Authorization")
            captured["payload"] = json.loads(request.data)
            captured["timeout"] = timeout
            return {
                "id": "req-1",
                "model": "hy3",
                "choices": [{"message": {"content": '```json\n{"ok": true}\n```'}}],
                "usage": {"total_tokens": 12},
            }

        result, metadata = Hy3Client(settings(), transport).complete_json(
            system="system", user="user"
        )
        self.assertEqual(result, {"ok": True})
        self.assertEqual(metadata["request_id"], "req-1")
        self.assertEqual(captured["url"], "https://hy3.example.test/v1/chat/completions")
        self.assertEqual(captured["auth"], "Bearer test-secret")
        self.assertEqual(captured["payload"]["model"], "hy3")
        self.assertEqual(captured["payload"]["response_format"], {"type": "json_object"})
        self.assertEqual(captured["timeout"], 3)

    def test_redacts_authentication_failure(self) -> None:
        def transport(request: Any, timeout: float) -> dict[str, Any]:
            del request, timeout
            raise urllib.error.HTTPError(
                "https://hy3.example.test", 401, "test-secret", {}, io.BytesIO()
            )

        with self.assertRaises(Hy3Error) as raised:
            Hy3Client(settings(), transport).complete_json(system="s", user="u")
        self.assertNotIn("test-secret", str(raised.exception))

    def test_rejects_invalid_provider_json(self) -> None:
        def transport(request: Any, timeout: float) -> dict[str, Any]:
            del request, timeout
            return {"choices": [{"message": {"content": "not json"}}]}

        with self.assertRaisesRegex(Hy3Error, "invalid structured"):
            Hy3Client(settings(), transport).complete_json(system="s", user="u")


if __name__ == "__main__":
    unittest.main()
