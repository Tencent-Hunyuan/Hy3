"""Tests for hy3research.planner."""

import pytest
from hy3research.planner import generate_plan, PLAN_SYSTEM_PROMPT


class TestPlanner:
    def test_mock_plan_has_required_fields(self):
        plan = generate_plan("人工智能发展趋势", mock=True)
        assert "title" in plan
        assert "subtopics" in plan
        assert "report_outline" in plan
        assert len(plan["subtopics"]) >= 2
        assert len(plan["subtopics"]) <= 6
        for st in plan["subtopics"]:
            assert "query" in st
            assert "key_question" in st

    def test_mock_plan_title_contains_topic(self):
        plan = generate_plan("量子计算", mock=True)
        assert "量子计算" in plan["title"]

    def test_mock_plan_outline_not_empty(self):
        plan = generate_plan("气候变化", mock=True)
        assert len(plan["report_outline"]) >= 3

    def test_system_prompt_asks_for_json(self):
        assert "JSON" in PLAN_SYSTEM_PROMPT
        assert "研究计划" in PLAN_SYSTEM_PROMPT
        assert "subtopics" in PLAN_SYSTEM_PROMPT
