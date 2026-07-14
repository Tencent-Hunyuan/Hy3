"""测试公共 fixtures。

- ``fake_client``：根据真实提取出的来源块动态构建，确保引用可被本地核验；
- ``analysis_service``：使用 FakeHy3Client，不访问真实 Hy3 API；
- 真实 API 冒烟测试单独用 ``@pytest.mark.live_hy3`` 标记，默认不运行。
"""

from __future__ import annotations

from pathlib import Path

import pytest

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
from rulelens.services.analysis_service import AnalysisService

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_bytes() -> bytes:
    return (FIXTURES / "sample_rules.md").read_bytes()


@pytest.fixture
def sample_name() -> str:
    return "sample_rules.md"


@pytest.fixture
def indexed(sample_bytes: bytes, sample_name: str):
    doc = extract_text(sample_name, sample_bytes)
    return SourceIndexer().index(doc.pages)


def _make_scenarios(n: int = 6) -> ScenarioSet:
    return ScenarioSet(
        scenarios=[
            Scenario(
                scenario_id=f"C{i:03d}",
                title=f"边界情景 {i}",
                description=f"这是第 {i} 个用于检验规则理解的情景。",
                boundary_type="临界值",
                difficulty="EASY",
                related_rule_ids=["R001"],
                required_facts=[],
            )
            for i in range(1, n + 1)
        ]
    )


@pytest.fixture
def fake_client(indexed):
    blocks = indexed.blocks
    s0 = blocks[0]
    quote = s0.text[: min(20, len(s0.text))]
    rules = RuleExtractionResult(
        document_title="示例规则",
        document_summary="测试摘要",
        defined_terms={},
        rules=[
            Rule(
                rule_id="R001",
                title="人数上限",
                normalized_statement=s0.text,
                rule_type=RuleType.THRESHOLD,
                topic="团队",
                conditions=[],
                exceptions=[],
                consequences=[],
                related_rule_ids=[],
                citations=[Citation(source_id=s0.source_id, evidence_quote=quote)],
                confidence=0.9,
            )
        ],
    )
    scenarios = _make_scenarios(6)
    ambiguity = AmbiguityReport(issues=[])
    judgment = Judgment(
        scenario_id="C001",
        verdict=Verdict.NON_COMPLIANT,
        rationale_summary="团队人数达到上限边界，需结合其他条件判断。",
        applied_rule_ids=["R001"],
        citations=[Citation(source_id=s0.source_id, evidence_quote=quote)],
        missing_information=[],
        confidence=0.8,
    )
    return FakeHy3Client(
        responses={
            "RuleExtractionResult": rules,
            "ScenarioSet": scenarios,
            "AmbiguityReport": ambiguity,
            "Judgment": judgment,
        }
    )


@pytest.fixture
def analysis_service(fake_client) -> AnalysisService:
    settings = Settings(hy3_api_key="dummy", hy3_base_url="http://example", hy3_model="hy3")
    return AnalysisService(fake_client, settings)
