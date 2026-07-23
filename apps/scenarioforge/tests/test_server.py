from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.request

from scenarioforge.config import Settings
from scenarioforge.examples import EXAMPLES
from scenarioforge.server import create_server


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        settings = Settings(
            base_url="https://hy3.example.test/v1",
            api_key="",
            model="hy3",
            timeout_seconds=3,
            demo_mode=True,
        )
        cls.server = create_server("127.0.0.1", 0, settings)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def get_json(self, path: str) -> dict:
        with urllib.request.urlopen(f"{self.base_url}{path}") as response:
            self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
            return json.load(response)

    def post_json(self, path: str, payload: dict) -> tuple[int, dict]:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            try:
                return error.code, json.load(error)
            finally:
                error.close()

    def test_health_exposes_demo_mode(self) -> None:
        health = self.get_json("/api/health")
        self.assertEqual(health["mode"], "demo")
        self.assertFalse(health["live_ready"])

    def test_serves_frontend_with_csp(self) -> None:
        with urllib.request.urlopen(f"{self.base_url}/") as response:
            body = response.read().decode()
            self.assertIn("ScenarioForge", body)
            self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])

    def test_both_examples_complete_end_to_end(self) -> None:
        for source in EXAMPLES.values():
            status, result = self.post_json("/api/rehearse", source)
            self.assertEqual(status, 200)
            self.assertEqual(result["mode"], "demo")
            self.assertEqual(result["provider"]["calls"], 0)

    def test_demo_rejects_edited_input(self) -> None:
        source = dict(EXAMPLES["campus-night-market"])
        source["title"] = "Edited plan"
        status, result = self.post_json("/api/rehearse", source)
        self.assertEqual(status, 400)
        self.assertIn("require live Hy3", result["error"])


if __name__ == "__main__":
    unittest.main()
