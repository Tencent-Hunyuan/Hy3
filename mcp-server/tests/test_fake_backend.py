# Copyright 2026 Tencent Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Fake backend: OpenAI wire-format compliance, routing, determinism."""

from __future__ import annotations

import httpx
import pytest
from openai import AsyncOpenAI

from hy3_mcp.fake_backend import OFFLINE_BANNER, build_fake_transport
from hy3_mcp.hy3_client import Hy3Client
from hy3_mcp.settings import Settings


def _fake_openai_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key="offline",
        base_url="http://hy3.fake/v1",
        http_client=httpx.AsyncClient(transport=build_fake_transport()),
    )


async def test_wire_format_parses_with_real_openai_sdk():
    """The fake's JSON must satisfy the production openai SDK models."""
    client = _fake_openai_client()
    resp = await client.chat.completions.create(
        model="hy3",
        messages=[
            {"role": "system", "content": "[hy3-mcp task=review]\nreview this"},
            {"role": "user", "content": "+x = eval(y)"},
        ],
    )
    assert resp.model == "hy3"
    assert resp.choices[0].finish_reason == "stop"
    assert resp.choices[0].message.content.startswith(OFFLINE_BANNER)
    assert resp.usage.total_tokens == (
        resp.usage.prompt_tokens + resp.usage.completion_tokens
    )


@pytest.mark.parametrize(
    ("task", "user", "marker"),
    [
        ("review", "+password = 'x'", "Code review (canned)"),
        ("docs", "[chunk 1 | a.md#0]\nHy3 has 256K context.", "Answer (grounded"),
        ("data", '```json\n{"rows": 3, "columns": []}\n```', "Data analysis (canned)"),
        ("research", "[source 1 | search:Some title <http://u>]\nsnippet", "Research notes"),
        ("mystery", "anything", "Generic canned reply"),
    ],
)
async def test_task_routing(task, user, marker, offline_settings):
    client = Hy3Client(offline_settings)
    reply = await client.chat(task=task, system="sys", user=user)
    assert reply.text.startswith(OFFLINE_BANNER)
    assert marker in reply.text


async def test_determinism_same_input_same_bytes(offline_settings):
    client = Hy3Client(offline_settings)
    kwargs = dict(task="review", system="sys", user="+cfg = eval(raw)\n+# TODO fix")
    first = await client.chat(**kwargs)
    second = await client.chat(**kwargs)
    assert first.text == second.text
    assert first.text.encode() == second.text.encode()


async def test_reasoning_effort_forwarded(offline_settings):
    """extra_body.chat_template_kwargs reaches the transport and is echoed."""
    client = Hy3Client(offline_settings)
    reply = await client.chat(
        task="review", system="s", user="u", reasoning_effort="high"
    )
    assert reply.text.rstrip().endswith("<!-- effort=high -->")


async def test_env_reasoning_effort_overrides_tool_default():
    settings = Settings.from_env(
        {"HY3_MCP_OFFLINE": "1", "HY3_REASONING_EFFORT": "low"}
    )
    client = Hy3Client(settings)
    reply = await client.chat(
        task="review", system="s", user="u", reasoning_effort="high"
    )
    assert reply.text.rstrip().endswith("<!-- effort=low -->")


async def test_usage_counter_accumulates(offline_settings):
    client = Hy3Client(offline_settings)
    assert client.usage.calls == 0
    await client.chat(task="docs", system="s", user="u")
    await client.chat(task="docs", system="s", user="u")
    assert client.usage.calls == 2
    assert client.usage.prompt_tokens > 0
    assert client.usage.completion_tokens > 0
