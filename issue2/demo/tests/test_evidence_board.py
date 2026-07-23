import json
import tempfile
import unittest
from pathlib import Path

from evidence_board import (
    DemoProvider,
    KnowledgeBase,
    OpenAICompatibleProvider,
    ResearchAgent,
    ValidationError,
    normalize_question,
)


DEMO_ROOT = Path(__file__).resolve().parents[1]


class NormalizeQuestionTests(unittest.TestCase):
    def test_collapses_whitespace(self):
        self.assertEqual(normalize_question("  Hy3   agent\n test  "), "Hy3 agent test")

    def test_rejects_short_question(self):
        with self.assertRaises(ValidationError):
            normalize_question("too short")

    def test_rejects_long_question(self):
        with self.assertRaises(ValidationError):
            normalize_question("x" * 501)


class KnowledgeBaseTests(unittest.TestCase):
    def setUp(self):
        self.knowledge = KnowledgeBase.from_directory(DEMO_ROOT / "knowledge")

    def test_search_returns_relevant_source(self):
        results = self.knowledge.search("Hy3 295B 激活参数")
        self.assertTrue(results)
        self.assertEqual(results[0]["id"], "model")

    def test_search_order_is_stable(self):
        first = [item["id"] for item in self.knowledge.search("Hy3 tool calling 模型")]
        second = [item["id"] for item in self.knowledge.search("Hy3 tool calling 模型")]
        self.assertEqual(first, second)

    def test_empty_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                KnowledgeBase.from_directory(Path(directory))


class ProviderPayloadTests(unittest.TestCase):
    def test_openrouter_reasoning_shape(self):
        provider = OpenAICompatibleProvider(
            base_url="https://openrouter.ai/api/v1",
            api_key="test",
            model="tencent/hy3",
            provider_kind="openrouter",
        )
        payload = provider.build_payload([{"role": "user", "content": "hello"}], [])
        self.assertEqual(payload["reasoning"], {"effort": "low"})
        self.assertNotIn("chat_template_kwargs", payload)

    def test_selfhost_reasoning_shape(self):
        provider = OpenAICompatibleProvider(
            base_url="http://127.0.0.1:8000/v1/",
            api_key="EMPTY",
            model="hy3",
        )
        payload = provider.build_payload([{"role": "user", "content": "hello"}], [])
        self.assertEqual(payload["chat_template_kwargs"], {"reasoning_effort": "low"})
        self.assertEqual(provider.base_url, "http://127.0.0.1:8000/v1")


class AgentTests(unittest.TestCase):
    def test_demo_runs_tool_then_returns_grounded_output(self):
        agent = ResearchAgent(DemoProvider(), KnowledgeBase.from_directory(DEMO_ROOT / "knowledge"))
        result = agent.run("请解释 Hy3 模型规模、上下文和工具调用部署要求。")
        self.assertEqual(result["mode"], "demo")
        self.assertGreaterEqual(len(result["trace"]), 1)
        self.assertGreaterEqual(len(result["evidence"]), 1)
        self.assertIn("未调用 Hy3", result["answer"])


if __name__ == "__main__":
    unittest.main()
