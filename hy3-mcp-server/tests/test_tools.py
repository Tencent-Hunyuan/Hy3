import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from hy3_mcp_server.tools import ask, file_analyze


@pytest.fixture
def mock_chat_completion():
    return ChatCompletion(
        id="chatcmpl-test",
        model="hy3",
        object="chat.completion",
        created=1234567890,
        choices=[
            Choice(
                index=0,
                message=ChatCompletionMessage(
                    role="assistant",
                    content="Mock response from Hy3",
                ),
                finish_reason="stop",
            )
        ],
    )


@pytest.mark.asyncio
async def test_ask_hy3(mock_chat_completion):
    with (
        patch.dict(os.environ, {"HY3_API_KEY": "sk-test"}),
        patch("hy3_mcp_server.hy3_client.OpenAI") as MockOpenAI,
    ):
        mock_instance = MagicMock()
        mock_instance.chat.completions.create.return_value = mock_chat_completion
        MockOpenAI.return_value = mock_instance

        ask._client = None
        result = await ask.ask_hy3("Test prompt", "high")
        assert result == "Mock response from Hy3"


@pytest.mark.asyncio
async def test_file_analyze(mock_chat_completion):
    test_file = Path(__file__).parent / "test_data.txt"
    test_file.write_text("Test file content for analysis.")
    try:
        with (
            patch.dict(os.environ, {"HY3_API_KEY": "sk-test"}),
            patch("hy3_mcp_server.hy3_client.OpenAI") as MockOpenAI,
        ):
            mock_instance = MagicMock()
            mock_instance.chat.completions.create.return_value = mock_chat_completion
            MockOpenAI.return_value = mock_instance

            file_analyze._client = None
            result = await file_analyze.file_analyze(str(test_file), "What is this?")
            assert result == "Mock response from Hy3"
    finally:
        test_file.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_file_analyze_not_found():
    file_analyze._client = None
    with pytest.raises(FileNotFoundError):
        await file_analyze.file_analyze("/nonexistent/file.txt", "test")
