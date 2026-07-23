from __future__ import annotations

import json
from pathlib import Path

import pytest

from hy3_leadintel_mcp.batch import score_leads
from hy3_leadintel_mcp.config import Settings
from hy3_leadintel_mcp.knowledge import query_documents, safe_child
from hy3_leadintel_mcp.tools import analyze_lead_tool, batch_score_leads_tool


ROOT = Path(__file__).resolve().parents[1]


def settings() -> Settings:
    return Settings(
        api_base="http://127.0.0.1:8000/v1",
        api_key=None,
        model="hy3",
        reasoning_effort="high",
        offline=True,
        timeout_seconds=5,
        root=ROOT,
    )


def test_analyze_lead_scores_relevant_motor_export_signal():
    result = analyze_lead_tool(
        settings(),
        {
            "company": "Aurora Motion",
            "industry": "manufacturing automation",
            "notes": "RFQ for motor export program with AI sales workflow.",
        },
    )

    assert result["priority"] in {"P0", "P1"}
    assert result["score"] >= 80
    assert "rfq" in [signal.lower() for signal in result["positive_signals"]]
    assert result["hy3_mode"] == "offline"


def test_query_documents_returns_grounded_citations():
    citations = query_documents(ROOT, "examples/knowledge_base", "robotics motor proof points", top_k=3)

    assert citations
    assert citations[0].path.endswith(".md")
    assert citations[0].score > 0


def test_safe_child_blocks_path_escape():
    with pytest.raises(ValueError):
        safe_child(ROOT, "../../etc/passwd")


def test_batch_score_leads_sorts_by_priority():
    rows = score_leads(ROOT, "examples/leads/sample_leads.csv", focus="motor export")

    assert [row["company"] for row in rows][:1] == ["Aurora Motion GmbH"]
    assert rows[0]["score"] >= rows[-1]["score"]


def test_batch_tool_can_write_report(tmp_path):
    temp_root = tmp_path
    examples = temp_root / "examples" / "leads"
    examples.mkdir(parents=True)
    (examples / "sample.csv").write_text(
        "company,industry,notes\nA,manufacturing,RFQ motor automation\nB,student,unclear personal research\n",
        encoding="utf-8",
    )
    local_settings = Settings("http://127.0.0.1:8000/v1", None, "hy3", "high", True, 5, temp_root)

    result = batch_score_leads_tool(local_settings, "examples/leads/sample.csv", output_path="out/report.json")

    assert result["report_path"] == "out/report.json"
    data = json.loads((temp_root / "out" / "report.json").read_text(encoding="utf-8"))
    assert data[0]["company"] == "A"
