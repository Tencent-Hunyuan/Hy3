# Copyright (C) 2026 Tencent. Licensed under the Apache License, Version 2.0.
# SPDX-License-Identifier: Apache-2.0
"""Deterministic fake backend: shape, routing rules, determinism, SDK roundtrip."""

from __future__ import annotations

import json

import httpx

from hyshell.fake_backend import make_fake_transport

URL = "http://fake.hy3.local/v1/chat/completions"


def _post(payload: dict) -> httpx.Response:
    with httpx.Client(transport=make_fake_transport()) as client:
        return client.post(URL, json=payload)


def _plan_body(request: str) -> dict:
    user = f"## TASK: plan\n## CWD: /w\n## OS: Linux\n## REQUEST: {request}"
    return {"model": "hy3", "messages": [{"role": "user", "content": user}]}


def _content(response: httpx.Response) -> dict:
    return json.loads(response.json()["choices"][0]["message"]["content"])


def test_chat_completion_shape():
    response = _post(_plan_body("统计一下这个项目里有多少个 Python 文件"))
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "chat.completion"
    assert data["id"].startswith("chatcmpl-fake-")
    assert data["created"] == 1700000000
    assert data["model"] == "hy3"
    assert data["choices"][0]["finish_reason"] == "stop"
    assert data["usage"]["total_tokens"] == (
        data["usage"]["prompt_tokens"] + data["usage"]["completion_tokens"]
    )


def test_same_prompt_same_bytes():
    body = _plan_body("统计一下这个项目里有多少个 Python 文件")
    assert _post(body).content == _post(body).content


def test_plan_rules_first_match_wins():
    # hits both the "count python files" rule (first) and the "largest files" rule
    plan = _content(_post(_plan_body("这里有多少个 Python 文件,里面最大的文件是哪个")))
    assert plan["command"] == "find . -type f -name '*.py' | wc -l"


def test_plan_dangerous_delete_logs():
    plan = _content(_post(_plan_body("把 logs 目录下的日志全部删掉")))
    assert plan["command"] == "rm -rf logs/*.log"
    assert plan["risk"] == "dangerous"
    assert plan["risk_reasons"]


def test_plan_fallback_is_honest_noop():
    plan = _content(_post(_plan_body("帮我泡一杯咖啡")))
    assert plan["command"] == "true"
    assert "伪后端" in plan["explanation"]
    assert plan["risk"] == "safe"


def _fix_body(command: str, stderr: str, listing: str) -> dict:
    user = (
        "## TASK: fix\n## CWD: /w\n## OS: Linux\n## REQUEST: 看文件\n"
        f"## COMMAND: {command}\n## EXIT: 1\n## STDERR: {stderr}\n## DIR: {listing}"
    )
    return {"model": "hy3", "messages": [{"role": "user", "content": user}]}


def test_fix_rule_uses_dir_listing():
    fix = _content(
        _post(
            _fix_body(
                "head -n 5 report.txt",
                "head: cannot open 'report.txt' for reading: No such file or directory",
                "big data.csv logs report.md src",
            )
        )
    )
    assert fix["command"] == "head -n 5 report.md"
    assert fix["confidence"] == "high"
    assert "report.md" in fix["diagnosis"]


def test_fix_falls_back_without_matching_dir_entry():
    fix = _content(
        _post(
            _fix_body(
                "head -n 5 report.txt",
                "head: cannot open 'report.txt' for reading: No such file or directory",
                "big data.csv logs src",  # no report.md
            )
        )
    )
    assert fix["command"] == "ls -la"
    assert fix["confidence"] == "low"


def test_alt_rule_for_rm_rf():
    user = (
        "## TASK: alt\n## CWD: /w\n## OS: Linux\n## REQUEST: 删日志\n"
        "## REJECTED: rm -rf logs/*.log\n## RISK_REASONS: 不可恢复"
    )
    alt = _content(_post({"model": "hy3", "messages": [{"role": "user", "content": user}]}))
    assert alt["command"] == "find logs -name '*.log' -mtime +30 -print"
    assert alt["risk"] == "caution"


def test_usage_tokens_deterministic():
    body = _plan_body("列出所有文件包括隐藏文件")
    user = body["messages"][0]["content"]
    data = _post(body).json()
    assert data["usage"]["prompt_tokens"] == len(user) // 4


def test_unknown_path_404():
    with httpx.Client(transport=make_fake_transport()) as client:
        assert client.post("http://fake.hy3.local/v1/embeddings", json={}).status_code == 404


def test_openai_sdk_roundtrip():
    from openai import OpenAI

    client = OpenAI(
        api_key="OFFLINE",
        base_url="http://fake.hy3.local/v1",
        http_client=httpx.Client(transport=make_fake_transport()),
    )
    response = client.chat.completions.create(
        model="hy3",
        messages=[
            {
                "role": "user",
                "content": "## TASK: plan\n## CWD: /w\n## OS: Linux\n## REQUEST: 磁盘占用多大",
            }
        ],
        temperature=0.9,
        top_p=1.0,
    )
    plan = json.loads(response.choices[0].message.content)
    assert plan["command"] == "du -sh ."
    assert response.usage.total_tokens > 0
