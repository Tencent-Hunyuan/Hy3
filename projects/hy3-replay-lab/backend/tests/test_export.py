# ruff: noqa: RUF001
import json
from pathlib import Path

import pytest

from replaylab import (
    ReplayLabService,
    StaticProvider,
    TaskSpec,
    export_report_json,
    export_report_markdown,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_json(relative_path: str) -> dict[str, object]:
    return json.loads((PROJECT_ROOT / relative_path).read_text(encoding="utf-8"))


@pytest.mark.asyncio
async def test_report_exports_complete_json_and_evidence_linked_markdown() -> None:
    task = TaskSpec.model_validate(load_json("fixtures/coding-loop/input.json"))
    report = await ReplayLabService(
        StaticProvider(load_json("fixtures/coding-loop/provider-output.json"))
    ).analyze(task)

    json_export = export_report_json(report)
    markdown_export = export_report_markdown(report)

    assert json.loads(json_export)["report_id"] == report.report_id
    assert "# 轨迹复盘报告：修复 slugify 的连续分隔符" in markdown_export
    assert "## 验收覆盖" in markdown_export
    assert "step-006-repeat-patch" in markdown_export
    assert "ev-repeat-failure" in markdown_export
    assert "## 最小重放计划" in markdown_export
    assert "raw chain of thought" not in markdown_export.casefold()
