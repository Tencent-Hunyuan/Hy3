# Copyright (C) 2026 Tencent. Licensed under the Apache License, Version 2.0.
# SPDX-License-Identifier: Apache-2.0
"""JSONL history store."""

from __future__ import annotations

import json

from hyshell.history import HistoryStore
from hyshell.schema import RiskLevel, TurnRecord


def _record(request: str = "统计文件", exit_code: int = 0) -> TurnRecord:
    return TurnRecord(
        ts="2026-07-18T00:00:00+00:00",
        request=request,
        command="ls",
        source="plan",
        risk_final=RiskLevel.SAFE,
        executed=True,
        exit_code=exit_code,
        mode="fake",
    )


def test_jsonl_appended(tmp_path):
    store = HistoryStore(tmp_path / "home")
    store.append(_record("第一条"))
    store.append(_record("第二条"))
    lines = (tmp_path / "home" / "history.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["request"] == "第一条"  # ensure_ascii=False keeps Chinese readable
    assert "第一条" in lines[0]
    assert first["risk_final"] == "SAFE"


def test_load_last_n(tmp_path):
    store = HistoryStore(tmp_path / "home")
    for index in range(5):
        store.append(_record(f"req-{index}"))
    last_two = store.load_last(2)
    assert [e["request"] for e in last_two] == ["req-3", "req-4"]


def test_load_missing_file_is_empty(tmp_path):
    assert HistoryStore(tmp_path / "nope").load_last() == []


def test_corrupt_line_skipped(tmp_path):
    store = HistoryStore(tmp_path / "home")
    store.append(_record("好的"))
    with store.path.open("a", encoding="utf-8") as handle:
        handle.write("{corrupt json\n")
    store.append(_record("坏行之后"))
    entries = store.load_last(10)
    assert [e["request"] for e in entries] == ["好的", "坏行之后"]
