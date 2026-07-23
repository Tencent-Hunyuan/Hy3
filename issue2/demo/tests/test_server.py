import json
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from evidence_board import DemoProvider, KnowledgeBase, ResearchAgent
from server import make_server


DEMO_ROOT = Path(__file__).resolve().parents[1]


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        agent = ResearchAgent(DemoProvider(), KnowledgeBase.from_directory(DEMO_ROOT / "knowledge"))
        cls.server = make_server("127.0.0.1", 0, agent)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_health_reports_demo_mode(self):
        with urllib.request.urlopen(f"{self.base_url}/api/health") as response:
            payload = json.load(response)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["mode"], "demo")

    def test_research_endpoint(self):
        request = urllib.request.Request(
            f"{self.base_url}/api/research",
            data=json.dumps({"question": "请解释 Hy3 的 Agent 工具调用和上下文能力。"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            payload = json.load(response)
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["trace"])

    def test_non_json_is_rejected_with_415(self):
        request = urllib.request.Request(
            f"{self.base_url}/api/research",
            data=b"question=not-json",
            headers={"Content-Type": "text/plain"},
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request)
        try:
            self.assertEqual(caught.exception.code, 415)
        finally:
            caught.exception.close()

    def test_short_question_is_rejected_with_400(self):
        request = urllib.request.Request(
            f"{self.base_url}/api/research",
            data=json.dumps({"question": "short"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request)
        try:
            self.assertEqual(caught.exception.code, 400)
        finally:
            caught.exception.close()


if __name__ == "__main__":
    unittest.main()
