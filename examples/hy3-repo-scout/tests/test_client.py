from unittest import TestCase

from hy3_repo_scout.client import create_chat_completion, reasoning_body
from hy3_repo_scout.config import Settings


class FakeCompletions:
    def __init__(self) -> None:
        self.request = None

    def create(self, **request):
        self.request = request
        return {"choices": [{"message": {"content": "ok"}}]}


class FakeClient:
    def __init__(self) -> None:
        self.chat = type("Chat", (), {})()
        self.chat.completions = FakeCompletions()


class ClientTests(TestCase):
    def test_openrouter_uses_standard_reasoning_effort(self) -> None:
        settings = Settings(api_key="test", reasoning_effort="high")
        self.assertEqual(reasoning_body(settings), {"reasoning": {"effort": "high"}})

    def test_no_think_maps_to_openrouter_minimal(self) -> None:
        settings = Settings(api_key="test", reasoning_effort="no_think")
        self.assertEqual(reasoning_body(settings), {"reasoning": {"effort": "minimal"}})

    def test_other_openai_compatible_endpoints_use_hy3_template_control(self) -> None:
        settings = Settings(
            api_key="test",
            base_url="https://hy3.example.com/v1",
            reasoning_effort="low",
        )
        self.assertEqual(
            reasoning_body(settings),
            {"chat_template_kwargs": {"reasoning_effort": "low"}},
        )

    def test_chat_request_includes_tools_and_provider_body(self) -> None:
        client = FakeClient()
        settings = Settings(api_key="test")
        tools = [{"type": "function", "function": {"name": "read_file"}}]

        create_chat_completion(client, settings, [{"role": "user", "content": "hi"}], tools)

        request = client.chat.completions.request
        self.assertEqual(request["extra_body"], {"reasoning": {"effort": "high"}})
        self.assertEqual(request["tool_choice"], "auto")
        self.assertEqual(request["tools"], tools)
