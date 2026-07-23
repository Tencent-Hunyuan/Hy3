"""Tests for hy3research.client mock mode."""

import json
import pytest
from hy3research.client import MockClient, get_client


class TestMockClient:
    def test_mock_returns_json_for_plan_prompt(self):
        client = MockClient()
        messages = [
            {"role": "system", "content": "输出JSON格式的研究计划"},
            {"role": "user", "content": "test topic"},
        ]
        result = client.chat(messages)
        assert isinstance(result, str)
        # Should be parseable JSON
        data = json.loads(result)
        assert "title" in data
        assert "subtopics" in data

    def test_mock_returns_text_for_general_prompt(self):
        client = MockClient()
        messages = [
            {"role": "user", "content": "write a report about AI"},
        ]
        result = client.chat(messages)
        assert isinstance(result, str)
        assert len(result) > 50

    def test_mock_client_not_None(self):
        client = get_client(mock=True)
        assert isinstance(client, MockClient)
