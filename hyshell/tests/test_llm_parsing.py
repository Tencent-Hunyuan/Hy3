# Copyright (C) 2026 Tencent. Licensed under the Apache License, Version 2.0.
# SPDX-License-Identifier: Apache-2.0
"""JSON extraction tolerance + real-SDK prompt/wire assertions via spy transport."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from hyshell.config import Settings
from hyshell.llm import Hy3Client, ShellContext, extract_json_block
from hyshell.schema import CommandPlan, ExecutionResult, ModelOutputError, RiskLevel


def test_extract_json_plain():
    assert extract_json_block('{"command": "ls"}') == {"command": "ls"}


def test_extract_json_fenced():
    text = '好的,方案如下:\n```json\n{"command": "ls", "risk": "safe"}\n```\n'
    assert extract_json_block(text)["command"] == "ls"


def test_extract_json_with_prose():
    text = '先说结论。{"command": "du -sh ."} 以上就是方案。'
    assert extract_json_block(text)["command"] == "du -sh ."


def test_extract_json_nested_braces_and_string_braces():
    payload = {"command": "awk '{print $1}'", "meta": {"note": "含 } 花括号"}}
    text = "前缀 " + json.dumps(payload, ensure_ascii=False) + " 后缀"
    assert extract_json_block(text) == payload


def test_extract_invalid_raises_with_snippet():
    with pytest.raises(ModelOutputError) as excinfo:
        extract_json_block("这不是 JSON,一点都不像。")
    assert "这不是 JSON" in str(excinfo.value)


def test_extract_top_level_array_rejected():
    with pytest.raises(ModelOutputError):
        extract_json_block('["not", "an", "object"]')


def _client_with_content(content: str, tmp_path: Path) -> Hy3Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-x",
                "object": "chat.completion",
                "created": 1700000000,
                "model": "hy3",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": content},
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    settings = Settings.from_env({"HYSHELL_HOME": str(tmp_path)}, offline=True)
    return Hy3Client(settings, transport=httpx.MockTransport(handler))


def test_plan_missing_command_rejected(tmp_path):
    client = _client_with_content('{"explanation": "没给命令", "risk": "safe"}', tmp_path)
    with pytest.raises(ModelOutputError) as excinfo:
        client.plan("随便", ShellContext(cwd=tmp_path))
    assert "CommandPlan" in str(excinfo.value)


def test_plan_empty_command_rejected(tmp_path):
    client = _client_with_content(
        '{"command": "  ", "explanation": "空命令", "risk": "safe"}', tmp_path
    )
    with pytest.raises(ModelOutputError):
        client.plan("随便", ShellContext(cwd=tmp_path))


def test_risk_coercion_accepts_case_variants():
    plan = CommandPlan.model_validate(
        {"command": "ls", "explanation": "x", "risk": "SAFE"}
    )
    assert plan.risk is RiskLevel.SAFE
    plan2 = CommandPlan.model_validate(
        {"command": "ls", "explanation": "x", "risk": "Dangerous"}
    )
    assert plan2.risk is RiskLevel.DANGEROUS


def test_client_sends_task_marker_and_model_name(spy_transport, tmp_path):
    settings = Settings.from_env({"HYSHELL_HOME": str(tmp_path)}, offline=True)
    client = Hy3Client(settings, transport=spy_transport)
    plan = client.plan("统计一下这个项目里有多少个 Python 文件", ShellContext(cwd=tmp_path))
    assert plan.command == "find . -type f -name '*.py' | wc -l"
    assert len(spy_transport.requests) == 1
    request = spy_transport.requests[0]
    assert request.url.path.endswith("/chat/completions")
    body = json.loads(request.content.decode("utf-8"))
    assert body["model"] == "hy3"
    assert body["temperature"] == 0.9
    assert body["top_p"] == 1.0
    assert "chat_template_kwargs" not in body  # reasoning_effort unset → not sent
    user = body["messages"][-1]["content"]
    assert user.startswith("## TASK: plan")
    assert "## REQUEST: 统计一下这个项目里有多少个 Python 文件" in user


def test_fix_prompt_contains_stderr_and_listing(spy_transport, tmp_path):
    settings = Settings.from_env({"HYSHELL_HOME": str(tmp_path)}, offline=True)
    client = Hy3Client(settings, transport=spy_transport)
    result = ExecutionResult(
        command="head -n 5 report.txt",
        exit_code=1,
        stdout="",
        stderr="head: cannot open 'report.txt' for reading: No such file or directory",
        duration_s=0.01,
    )
    fix = client.suggest_fix(
        "看看 report.txt 的前 5 行",
        "head -n 5 report.txt",
        result,
        "big data.csv logs report.md src",
        ShellContext(cwd=tmp_path),
    )
    assert fix.command == "head -n 5 report.md"
    user = json.loads(spy_transport.requests[0].content)["messages"][-1]["content"]
    assert "## TASK: fix" in user
    assert "No such file" in user
    assert "report.md" in user
    assert "## EXIT: 1" in user


def test_reasoning_effort_passthrough_when_set(spy_transport, tmp_path):
    settings = Settings.from_env(
        {"HYSHELL_HOME": str(tmp_path), "HY3_REASONING_EFFORT": "low"}, offline=True
    )
    client = Hy3Client(settings, transport=spy_transport)
    client.plan("列出所有文件包括隐藏文件", ShellContext(cwd=tmp_path))
    body = json.loads(spy_transport.requests[0].content)
    assert body["chat_template_kwargs"] == {"reasoning_effort": "low"}


def test_alt_prompt_contains_rejected_command(spy_transport, tmp_path):
    settings = Settings.from_env({"HYSHELL_HOME": str(tmp_path)}, offline=True)
    client = Hy3Client(settings, transport=spy_transport)
    rejected = CommandPlan(
        command="rm -rf logs/*.log",
        explanation="删除日志",
        risk=RiskLevel.DANGEROUS,
        risk_reasons=["不可恢复"],
    )
    alt = client.safer_alternative(rejected, "把日志删掉", ShellContext(cwd=tmp_path))
    assert alt.command == "find logs -name '*.log' -mtime +30 -print"
    user = json.loads(spy_transport.requests[0].content)["messages"][-1]["content"]
    assert "## TASK: alt" in user
    assert "## REJECTED: rm -rf logs/*.log" in user
    assert "不可恢复" in user
