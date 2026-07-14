"""无头 UI 端到端测试（使用 Streamlit AppTest + FakeHy3Client，不调用真实 API）。

验证：应用可启动 -> 载入示例 -> 点击「开始分析」-> 结果页（规则地图 / 情景 / 歧义 / 原文 / 导出）正常渲染。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from rulelens.config import Settings
from rulelens.ingestion.extractors import extract_text
from rulelens.ingestion.source_indexer import SourceIndexer
from rulelens.llm.hy3_client import FakeHy3Client
from rulelens.models import (
    AmbiguityReport,
    Citation,
    Judgment,
    Rule,
    RuleExtractionResult,
    RuleType,
    Scenario,
    ScenarioSet,
    Verdict,
)
from rulelens.ui import components


def _demo_fake():
    demo = Path(__file__).resolve().parents[1] / "data" / "samples" / "demo_contest_rules.md"
    doc = extract_text(demo.name, demo.read_bytes())
    idx = SourceIndexer().index(doc.pages)
    s0 = idx.blocks[0]
    quote = s0.text[: min(20, len(s0.text))]

    rules = RuleExtractionResult(
        document_title="创新编程大赛报名规则",
        document_summary="关于报名截止、团队人数与材料补交的规则。",
        defined_terms={},
        rules=[
            Rule(
                rule_id="R001",
                title="报名截止",
                normalized_statement="报名截止时间为 2026 年 4 月 30 日 23:59。",
                rule_type=RuleType.DEADLINE,
                topic="报名",
                conditions=[],
                exceptions=[],
                consequences=[],
                related_rule_ids=[],
                citations=[Citation(source_id=s0.source_id, evidence_quote=quote)],
                confidence=0.9,
            ),
            Rule(
                rule_id="R002",
                title="团队人数",
                normalized_statement="团队人数 2 至 5 人。",
                rule_type=RuleType.THRESHOLD,
                topic="团队",
                conditions=[],
                exceptions=[],
                consequences=[],
                related_rule_ids=["R001"],
                citations=[Citation(source_id=s0.source_id, evidence_quote=quote)],
                confidence=0.9,
            ),
        ],
    )
    scenarios = ScenarioSet(
        scenarios=[
            Scenario(
                scenario_id=f"C{i:03d}",
                title=f"情景{i}",
                description=f"描述{i}",
                boundary_type="临界值",
                difficulty="EASY",
                related_rule_ids=["R001", "R002"],
                required_facts=[],
            )
            for i in range(1, 7)
        ]
    )
    ambiguity = AmbiguityReport(issues=[])
    judgment = Judgment(
        scenario_id="C001",
        verdict=Verdict.INSUFFICIENT_INFO,
        rationale_summary="截止后补交材料存在条款冲突，无法唯一判断。",
        applied_rule_ids=["R001"],
        citations=[Citation(source_id=s0.source_id, evidence_quote=quote)],
        missing_information=["补交材料是否在工作日受理"],
        confidence=0.8,
    )
    return {
        "RuleExtractionResult": rules,
        "ScenarioSet": scenarios,
        "AmbiguityReport": ambiguity,
        "Judgment": judgment,
    }


class _PatchedFake(FakeHy3Client):
    def __init__(self, settings=None):  # 兼容 Hy3Client(settings) 调用
        super().__init__(responses=_demo_fake())


@pytest.fixture
def patched(monkeypatch):
    monkeypatch.setattr(components, "Hy3Client", _PatchedFake)
    monkeypatch.setattr(
        components,
        "load_settings",
        lambda: Settings(hy3_api_key="dummy", hy3_base_url="http://example", hy3_model="hy3"),
    )


def test_app_boots_and_analyzes(patched):
    at = AppTest.from_file("app.py")
    at.run()
    assert "规则透镜" in at.title[0].value
    # 上传控件与示例按钮存在
    at.button("sample_contest").click().run()
    at.button("start_analysis").click().run()

    # 结果页渲染：五个 Tab + 摘要指标 + 规则地图内容
    assert at.tabs  # 存在 Tabs 组件
    assert len(at.tabs) >= 1
    # 摘要指标以 metric 形式渲染
    assert any(m.label == "引用核验通过率" for m in at.metric)
    # 默认第一个 Tab（规则地图）已渲染出规则标题
    assert any("报名截止" in m.value for m in at.markdown)


def test_app_shows_unconfigured_warning_without_settings():
    at = AppTest.from_file("app.py")
    at.run()
    # 未配置时侧边栏以 error 形式提示
    assert at.error
    assert any("未配置" in e.value for e in at.error)
