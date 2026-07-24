from __future__ import annotations

import json
from pathlib import Path

import pytest

from hy3_leadintel_mcp.batch import score_leads
from hy3_leadintel_mcp.config import Settings
from hy3_leadintel_mcp.hy3_client import Hy3Client
from hy3_leadintel_mcp.knowledge import query_documents, safe_child
from hy3_leadintel_mcp.server import build_app
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


def test_real_hy3_payload_uses_top_level_chat_template_kwargs(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return b'{"choices":[{"message":{"content":"ok"}}]}'

    def fake_urlopen(request, timeout):
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    real_settings = Settings(
        api_base="http://127.0.0.1:8000/v1",
        api_key="test-key",
        model="hy3",
        reasoning_effort="high",
        offline=False,
        timeout_seconds=7,
        root=ROOT,
    )

    result = Hy3Client(real_settings).complete("system", "user", reasoning_effort="low")

    assert result.content == "ok"
    assert captured["timeout"] == 7
    assert captured["payload"]["chat_template_kwargs"]["reasoning_effort"] == "low"
    assert "extra_body" not in captured["payload"]


def test_mcp_tool_parameters_include_descriptions():
    app = build_app()
    tools = app._tool_manager._tools

    for tool_name in ["analyze_lead", "query_knowledge_base", "generate_outreach_plan", "batch_score_leads"]:
        for param_name, schema in tools[tool_name].parameters["properties"].items():
            assert schema.get("description"), f"{tool_name}.{param_name} is missing a description"
