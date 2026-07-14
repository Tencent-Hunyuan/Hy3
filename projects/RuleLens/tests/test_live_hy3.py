"""真实 Hy3 API 冒烟测试（默认不运行）。

仅在配置了真实环境变量时才执行；CI 中不消耗真实 API，除非仓库维护者明确配置 Secret。
运行方式：
    pytest -m live_hy3
"""

from __future__ import annotations

import pytest

from rulelens.config import load_settings
from rulelens.llm.hy3_client import Hy3Client
from rulelens.models import Verdict
from rulelens.services.analysis_service import AnalysisService

pytestmark = pytest.mark.live_hy3

_SAMPLE = (
    "团队人数上限为 5 人。报名截止时间为 2026 年 4 月 30 日 23:59。"
    "每名参赛者只能加入一个团队，不得重复报名。"
)


def test_live_analysis_runs_end_to_end():
    settings = load_settings()
    if not settings.is_configured:
        pytest.skip("未配置 HY3_API_KEY / HY3_BASE_URL / HY3_MODEL，跳过真实冒烟测试。")

    service = AnalysisService(Hy3Client(settings), settings)
    bundle = service.analyze_document("live_sample.md", _SAMPLE.encode("utf-8"))

    assert bundle.sources
    assert bundle.rule_result.rules
    assert 6 <= len(bundle.scenario_set.scenarios) <= 12
    assert bundle.ambiguity_report is not None
    # 规则引用应被本地核验
    assert bundle.rule_result.rules[0].citations[0].status is not None

    # 单题裁决
    first = bundle.scenario_set.scenarios[0]
    attempt = service.judge_scenario(bundle, first.scenario_id, Verdict.INSUFFICIENT_INFO)
    assert attempt.judgment.verdict is not None
