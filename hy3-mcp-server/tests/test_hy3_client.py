import os
from unittest.mock import MagicMock, patch

import pytest

from hy3_mcp_server.hy3_client import Hy3Client


def test_requires_api_key():
    with pytest.raises(ValueError, match="HY3_API_KEY"):
        with patch.dict(os.environ, {}, clear=True):
            Hy3Client()


def test_uses_env_vars():
    with patch.dict(os.environ, {
        "HY3_API_KEY": "sk-test",
        "HY3_BASE_URL": "https://custom.example.com/v1",
        "HY3_MODEL_NAME": "hy3-custom",
    }):
        client = Hy3Client()
        assert client.model == "hy3-custom"
        assert str(client.client.base_url) == "https://custom.example.com/v1/"


def test_default_base_url():
    with patch.dict(os.environ, {"HY3_API_KEY": "sk-test"}, clear=True):
        client = Hy3Client()
        assert str(client.client.base_url) == "https://tokenhub-intl.tencentmaas.com/v1/"


def test_chat_calls_openai():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Test response"

    with patch.dict(os.environ, {"HY3_API_KEY": "sk-test"}):
        client = Hy3Client()
        client.client.chat.completions.create = MagicMock(return_value=mock_response)
        result = client.chat(
            messages=[{"role": "user", "content": "Hello"}],
            reasoning_effort="high",
        )
        assert result == "Test response"
        client.client.chat.completions.create.assert_called_once()
        call_kwargs = client.client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "hy3"
        assert call_kwargs["extra_body"]["chat_template_kwargs"]["reasoning_effort"] == "high"
