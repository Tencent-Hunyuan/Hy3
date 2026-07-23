from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from hy3_data_analyst import server


@pytest.fixture
def configured_dataset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    dataset = tmp_path / "metrics.csv"
    dataset.write_text("team,score\nA,10\nB,20\n", encoding="utf-8")
    monkeypatch.setenv("HY3_DATA_DIR", str(tmp_path))
    return dataset


def test_profile_tool_returns_structured_result(configured_dataset: Path) -> None:
    result = server.profile_dataset(configured_dataset.name, sample_rows=1)

    assert result["rows_scanned"] == 2
    assert result["sample_rows"] == [{"team": "A", "score": "10"}]


@pytest.mark.asyncio
async def test_analyze_tool_calls_hy3_with_grounded_context(
    configured_dataset: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    async def fake_call(messages: Any, **kwargs: Any) -> str:
        captured["messages"] = messages
        captured.update(kwargs)
        return "Team B has the higher observed score."

    monkeypatch.setattr(server, "call_hy3", fake_call)

    result = await server.analyze_dataset(
        configured_dataset.name,
        "Which team leads?",
        reasoning_effort="low",
    )

    assert result["analysis"].startswith("Team B")
    assert captured["reasoning_effort"] == "low"
    prompt = captured["messages"][1]["content"]
    assert "Which team leads?" in prompt
    assert '"rows_scanned": 2' in prompt
    assert '"score": "20"' in prompt


@pytest.mark.asyncio
async def test_report_tool_requests_required_sections(
    configured_dataset: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    async def fake_call(messages: Any, **kwargs: Any) -> str:
        captured["messages"] = messages
        return "# Report\n\n## Executive summary\nB leads."

    monkeypatch.setattr(server, "call_hy3", fake_call)

    report = await server.generate_data_report(configured_dataset.name, "Help management decide")

    assert report.startswith("# Report")
    prompt = captured["messages"][1]["content"]
    assert "recommended actions" in prompt
    assert "limitations" in prompt


@pytest.mark.asyncio
async def test_rejects_blank_analysis_question(configured_dataset: Path) -> None:
    with pytest.raises(ValueError, match="question must not be empty"):
        await server.analyze_dataset(configured_dataset.name, "  ")
