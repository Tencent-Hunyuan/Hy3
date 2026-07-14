"""分析服务单元测试（使用 FakeHy3Client，不调用真实 API）。"""

from __future__ import annotations

import pytest
from httpx import Request, Response
from openai import APIStatusError
from pydantic import BaseModel

from rulelens.config import Settings
from rulelens.exceptions import FileTooLargeError
from rulelens.llm.hy3_client import FakeHy3Client, Hy3Client
from rulelens.llm.prompts import SYSTEM_PROMPT
from rulelens.models import (
    AmbiguityReport,
    Citation,
    CitationStatus,
    Judgment,
    Rule,
    RuleExtractionResult,
    RuleType,
    Scenario,
    ScenarioSet,
    Verdict,
)
from rulelens.services.analysis_service import AnalysisService


def _build_client(
    indexed, *, judgment_verdict: Verdict = Verdict.NON_COMPLIANT, dup_rules: bool = False
):
    s0 = indexed.blocks[0]
    quote = s0.text[: min(20, len(s0.text))]
    if dup_rules:
        rules = RuleExtractionResult(
            document_title="t",
            document_summary="s",
            defined_terms={},
            rules=[
                Rule(
                    rule_id="R001",
                    title="a",
                    normalized_statement=s0.text,
                    rule_type=RuleType.THRESHOLD,
                    topic="x",
                    citations=[Citation(source_id=s0.source_id, evidence_quote=quote)],
                    confidence=0.9,
                ),
                Rule(
                    rule_id="R001",
                    title="b",
                    normalized_statement=s0.text,
                    rule_type=RuleType.OTHER,
                    topic="x",
                    citations=[Citation(source_id=s0.source_id, evidence_quote=quote)],
                    confidence=0.9,
                ),
            ],
        )
    else:
        rules = RuleExtractionResult(
            document_title="t",
            document_summary="s",
            defined_terms={},
            rules=[
                Rule(
                    rule_id="R001",
                    title="a",
                    normalized_statement=s0.text,
                    rule_type=RuleType.THRESHOLD,
                    topic="x",
                    citations=[Citation(source_id=s0.source_id, evidence_quote=quote)],
                    confidence=0.9,
                )
            ],
        )
    scenarios = ScenarioSet(
        scenarios=[
            Scenario(
                scenario_id=f"C{i:03d}",
                title=f"情景{i}",
                description=f"描述{i}",
                boundary_type="v",
                difficulty="EASY",
                related_rule_ids=["R001"],
                required_facts=[],
            )
            for i in range(1, 7)
        ]
    )
    ambiguity = AmbiguityReport(issues=[])
    judgment = Judgment(
        scenario_id="C001",
        verdict=judgment_verdict,
        rationale_summary="依据规则判断。",
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


# --------------------------------------------------------------------------- #
def test_analyze_document_returns_bundle(analysis_service, sample_bytes, sample_name):
    bundle = analysis_service.analyze_document(sample_name, sample_bytes)
    assert bundle.schema_version == "1.0"
    assert bundle.sources
    assert bundle.rule_result.rules
    assert len(bundle.scenario_set.scenarios) >= 6
    # 引用被核验
    assert bundle.rule_result.rules[0].citations[0].status is not None


def test_call_order(analysis_service, sample_bytes, sample_name, fake_client):
    analysis_service.analyze_document(sample_name, sample_bytes)
    assert len(fake_client.calls) == 3
    # 第一轮为规则提取，且均使用系统约束
    for system, _user in fake_client.calls:
        assert SYSTEM_PROMPT in system


def test_progress_callback_emits_extraction_and_model_stages(
    fake_client, sample_bytes, sample_name
):
    settings = Settings(hy3_api_key="x", hy3_base_url="http://x", hy3_model="m")
    service = AnalysisService(fake_client, settings)
    messages: list[str] = []

    service.analyze_document(sample_name, sample_bytes, progress=messages.append)

    assert messages[:6] == [
        "① 提取文本与生成来源编号…",
        "② 生成规则提取并核验引用…",
        "②-1 正在请求模型提取规则…",
        "②-2 规则已返回，正在核验引用…",
        "③ 正在生成情景并重编号…",
        "④ 正在生成歧义报告并核验引用…",
    ]


def test_no_partial_bundle_on_missing_stage(indexed, sample_bytes, sample_name):
    s0 = indexed.blocks[0]
    quote = s0.text[: min(20, len(s0.text))]
    rules = RuleExtractionResult(
        document_title="t",
        document_summary="s",
        defined_terms={},
        rules=[
            Rule(
                rule_id="R001",
                title="a",
                normalized_statement=s0.text,
                rule_type=RuleType.THRESHOLD,
                topic="x",
                citations=[Citation(source_id=s0.source_id, evidence_quote=quote)],
                confidence=0.9,
            )
        ],
    )
    # 缺少 ScenarioSet 响应
    fake = FakeHy3Client(
        responses={"RuleExtractionResult": rules, "AmbiguityReport": AmbiguityReport(issues=[])}
    )
    settings = Settings(hy3_api_key="x", hy3_base_url="http://x", hy3_model="m")
    service = AnalysisService(fake, settings)
    with pytest.raises(RuntimeError):
        service.analyze_document(sample_name, sample_bytes)


def test_duplicate_rule_ids_renumbered(indexed, sample_bytes, sample_name):
    fake = _build_client(indexed, dup_rules=True)
    settings = Settings(hy3_api_key="x", hy3_base_url="http://x", hy3_model="m")
    service = AnalysisService(fake, settings)
    bundle = service.analyze_document(sample_name, sample_bytes)
    ids = [r.rule_id for r in bundle.rule_result.rules]
    assert ids == ["R001", "R002"]
    # 关联字段同步更新
    assert bundle.scenario_set.scenarios[0].related_rule_ids == ["R001"]


def test_judge_scores_correctly(analysis_service, sample_bytes, sample_name):
    bundle = analysis_service.analyze_document(sample_name, sample_bytes)
    attempt = analysis_service.judge_scenario(bundle, "C001", Verdict.NON_COMPLIANT)
    assert attempt.is_correct is True
    assert attempt.judgment.verdict == Verdict.NON_COMPLIANT


def test_insufficient_info_can_be_correct(indexed, sample_bytes, sample_name):
    fake = _build_client(indexed, judgment_verdict=Verdict.INSUFFICIENT_INFO)
    settings = Settings(hy3_api_key="x", hy3_base_url="http://x", hy3_model="m")
    service = AnalysisService(fake, settings)
    bundle = service.analyze_document(sample_name, sample_bytes)
    attempt = service.judge_scenario(bundle, "C001", Verdict.INSUFFICIENT_INFO)
    assert attempt.is_correct is True


def test_oversize_file_raises(indexed, sample_bytes, sample_name):
    # 通过极小的字符上限触发「提取后字符数超限」拒绝
    settings = Settings(hy3_api_key="x", hy3_base_url="http://x", hy3_model="m", max_chars=1)
    fake = _build_client(indexed)
    service = AnalysisService(fake, settings)
    with pytest.raises(FileTooLargeError):
        service.analyze_document(sample_name, sample_bytes)


def test_fake_llm_responses_fixture(sample_bytes, sample_name):
    """直接使用 fixtures/fake_llm_responses.json 驱动一次完整分析。"""
    import json
    from pathlib import Path

    raw = json.loads(
        (Path(__file__).parent / "fixtures" / "fake_llm_responses.json").read_text("utf-8")
    )
    fake = FakeHy3Client(raw_responses=raw)
    settings = Settings(hy3_api_key="x", hy3_base_url="http://x", hy3_model="m")
    service = AnalysisService(fake, settings)
    bundle = service.analyze_document(sample_name, sample_bytes)
    assert bundle.rule_result.rules[0].citations[0].status == CitationStatus.VERIFIED
    assert len(bundle.scenario_set.scenarios) >= 6


def test_reasoning_effort_uses_official_chat_template_shape_by_default():
    settings = Settings(
        hy3_api_key="x",
        hy3_base_url="http://x",
        hy3_model="m",
        hy3_reasoning_effort="high",
        hy3_enable_reasoning_param=True,
    )
    client = Hy3Client(settings)

    kwargs = client._build_kwargs("system", "user", None)

    assert kwargs["extra_body"] == {"chat_template_kwargs": {"reasoning_effort": "high"}}


def test_reasoning_effort_supports_direct_gateway_style():
    settings = Settings(
        hy3_api_key="x",
        hy3_base_url="http://x",
        hy3_model="m",
        hy3_reasoning_param_style="direct",
    )
    client = Hy3Client(settings)

    kwargs = client._build_kwargs("system", "user", "low")

    assert kwargs["extra_body"] == {"reasoning_effort": "low"}


def test_response_format_can_be_disabled():
    settings = Settings(
        hy3_api_key="x",
        hy3_base_url="http://x",
        hy3_model="m",
        hy3_enable_response_format=False,
    )
    client = Hy3Client(settings)
    captured: list[dict] = []

    class Payload(BaseModel):
        value: int

    def fake_call(kwargs: dict) -> str:
        captured.append(kwargs)
        return '{"value": 1}'

    client._call_with_retry = fake_call
    result = client.generate_validated("system", "user", Payload)

    assert result.value == 1
    assert "response_format" not in captured[0]


def test_unsupported_response_format_triggers_fallback():
    request = Request("POST", "http://x/v1/chat/completions")
    response = Response(400, request=request)
    exc = APIStatusError(
        "Unsupported response_format json_schema",
        response=response,
        body={"error": "unsupported"},
    )

    assert Hy3Client._should_retry_without_response_format(
        exc, {"response_format": {"type": "json_schema"}}
    )
    assert not Hy3Client._should_retry_without_response_format(exc, {})


def test_reasoning_effort_can_be_disabled():
    settings = Settings(
        hy3_api_key="x",
        hy3_base_url="http://x",
        hy3_model="m",
        hy3_enable_reasoning_param=False,
    )
    client = Hy3Client(settings)

    kwargs = client._build_kwargs("system", "user", "no_think")

    assert "extra_body" not in kwargs
