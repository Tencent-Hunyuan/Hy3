"""Tests for Hy3Client retry and timeout logic."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from openai import APITimeoutError, RateLimitError

from hy3_deep_research.config import Config
from hy3_deep_research.hy3_client import Hy3Client


def _make_config() -> Config:
    return Config(hunyuan_api_key="test-key", hunyuan_model="hy3")


def _make_fake_response(content: str = "hello"):
    """Create a fake OpenAI chat completion response."""
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def test_chat_success():
    """A normal call returns the content string."""
    client = Hy3Client(_make_config())
    fake_resp = _make_fake_response("Hy3 says hello")

    with patch.object(
        client._client.chat.completions, "create", return_value=fake_resp
    ):
        result = client.chat([{"role": "user", "content": "hi"}])

    assert result == "Hy3 says hello"


def test_chat_retries_on_timeout():
    """Timeout errors are retried, and a subsequent success is returned."""
    client = Hy3Client(_make_config())
    fake_resp = _make_fake_response("recovered")

    mock_create = MagicMock(
        side_effect=[
            APITimeoutError(request=MagicMock()),
            APITimeoutError(request=MagicMock()),
            fake_resp,
        ]
    )

    with patch.object(
        client._client.chat.completions, "create", mock_create
    ), patch("hy3_deep_research.hy3_client.time.sleep"):
        result = client.chat([{"role": "user", "content": "hi"}])

    assert result == "recovered"
    assert mock_create.call_count == 3


def test_chat_retries_on_rate_limit():
    """RateLimitError is retried."""
    client = Hy3Client(_make_config())
    fake_resp = _make_fake_response("ok after rate limit")

    # RateLimitError requires specific constructor args
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.headers = {}
    mock_response.text = "rate limited"

    mock_create = MagicMock(
        side_effect=[
            RateLimitError(
                message="rate limited",
                response=mock_response,
                body=mock_response.text,
            ),
            fake_resp,
        ]
    )

    with patch.object(
        client._client.chat.completions, "create", mock_create
    ), patch("hy3_deep_research.hy3_client.time.sleep"):
        result = client.chat([{"role": "user", "content": "hi"}])

    assert result == "ok after rate limit"
    assert mock_create.call_count == 2


def test_chat_raises_after_max_retries():
    """When all retries are exhausted, the last error is re-raised."""
    client = Hy3Client(_make_config())

    mock_create = MagicMock(
        side_effect=APITimeoutError(request=MagicMock())
    )

    with patch.object(
        client._client.chat.completions, "create", mock_create
    ), patch("hy3_deep_research.hy3_client.time.sleep"):
        with pytest.raises(APITimeoutError):
            client.chat([{"role": "user", "content": "hi"}])

    assert mock_create.call_count == 3  # 1 initial + 2 retries


def test_chat_does_not_retry_on_generic_error():
    """Non-transient errors (e.g. ValueError) are raised immediately."""
    client = Hy3Client(_make_config())

    mock_create = MagicMock(side_effect=ValueError("bad request"))

    with patch.object(
        client._client.chat.completions, "create", mock_create
    ):
        with pytest.raises(ValueError):
            client.chat([{"role": "user", "content": "hi"}])

    assert mock_create.call_count == 1  # no retries


def test_chat_passes_reasoning_effort_top():
    """The reasoning_effort parameter is passed as top-level extra_body (TokenHub default)."""
    client = Hy3Client(_make_config())  # default reasoning_format="top"
    fake_resp = _make_fake_response("ok")

    with patch.object(
        client._client.chat.completions, "create", return_value=fake_resp
    ) as mock_create:
        client.chat(
            [{"role": "user", "content": "think hard"}],
            reasoning_effort="high",
        )

    call_kwargs = mock_create.call_args.kwargs
    assert "extra_body" in call_kwargs
    assert call_kwargs["extra_body"]["reasoning_effort"] == "high"


def test_chat_passes_reasoning_effort_template():
    """The reasoning_effort parameter is passed via chat_template_kwargs (self-deployed)."""
    cfg = Config(hunyuan_api_key="test-key", hunyuan_model="hy3", reasoning_format="template")
    client = Hy3Client(cfg)
    fake_resp = _make_fake_response("ok")

    with patch.object(
        client._client.chat.completions, "create", return_value=fake_resp
    ) as mock_create:
        client.chat(
            [{"role": "user", "content": "think hard"}],
            reasoning_effort="high",
        )

    call_kwargs = mock_create.call_args.kwargs
    assert "extra_body" in call_kwargs
    assert "chat_template_kwargs" in call_kwargs["extra_body"]
    assert call_kwargs["extra_body"]["chat_template_kwargs"]["reasoning_effort"] == "high"
