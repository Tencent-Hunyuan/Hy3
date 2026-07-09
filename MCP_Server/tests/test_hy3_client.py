import asyncio

from hy3_mcp_server.config import Hy3Settings
from hy3_mcp_server.hy3_client import Hy3Client


class _Message:
    content = "ok"


class _Choice:
    message = _Message()


class _Response:
    choices = [_Choice()]


class _Completions:
    def __init__(self):
        self.params = None

    async def create(self, **params):
        self.params = params
        return _Response()


class _Chat:
    def __init__(self):
        self.completions = _Completions()


def test_chat_includes_hy3_reasoning_effort():
    asyncio.run(_run_chat_payload_test())


async def _run_chat_payload_test():
    client = Hy3Client(Hy3Settings(default_reasoning_effort="low", enable_reasoning_effort=True))
    fake_chat = _Chat()
    client._client.chat = fake_chat

    result = await client.chat([{"role": "user", "content": "hello"}], reasoning_effort="high")

    assert result == "ok"
    assert fake_chat.completions.params["model"] == "hy3"
    assert fake_chat.completions.params["extra_body"] == {
        "chat_template_kwargs": {"reasoning_effort": "high"}
    }


def test_chat_omits_reasoning_effort_by_default():
    asyncio.run(_run_default_payload_test())


async def _run_default_payload_test():
    client = Hy3Client(Hy3Settings())
    fake_chat = _Chat()
    client._client.chat = fake_chat

    result = await client.chat([{"role": "user", "content": "hello"}], reasoning_effort="high")

    assert result == "ok"
    assert "extra_body" not in fake_chat.completions.params
