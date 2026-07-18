"""Tests for the five MCP tool ``run`` functions and their input schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hy3_architecture_mcp import _runtime
from hy3_architecture_mcp.schemas import (
    AnalyzeProjectContextInput,
    ClarifyRequirementsInput,
    CreateImplementationPlanInput,
    GenerateTechnicalProposalInput,
    ReviewTechnicalProposalInput,
)
from hy3_architecture_mcp.tools import planning, proposal, requirements, review

from .conftest import FakeHy3Client

# --- Tool 1: clarify_requirements -----------------------------------------


async def test_clarify_requirements_ok():
    from hy3_architecture_mcp.schemas import ClarifyRequirementsOutput

    out = ClarifyRequirementsOutput(
        understood_goals=["g"],
        ambiguities=["a"],
        missing_information=["m"],
        clarifying_questions=["q1", "q2"],
        acceptance_criteria=["c"],
        assumptions=["s"],
    )
    _runtime._client = FakeHy3Client([out])
    data = ClarifyRequirementsInput(requirement="Build a knowledge base")
    result = await requirements.run(data)
    assert result.clarifying_questions == ["q1", "q2"]


async def test_clarify_requirements_caps_questions():
    from hy3_architecture_mcp.schemas import ClarifyRequirementsOutput

    out = ClarifyRequirementsOutput(
        understood_goals=[],
        ambiguities=[],
        missing_information=[],
        clarifying_questions=[f"q{i}" for i in range(10)],
        acceptance_criteria=[],
        assumptions=[],
    )
    _runtime._client = FakeHy3Client([out])
    data = ClarifyRequirementsInput(requirement="x", max_questions=3)
    result = await requirements.run(data)
    assert len(result.clarifying_questions) == 3


def test_clarify_input_rejects_empty_requirement():
    with pytest.raises(ValidationError):
        ClarifyRequirementsInput(requirement="")


def test_clarify_input_rejects_max_questions_out_of_range():
    with pytest.raises(ValidationError):
        ClarifyRequirementsInput(requirement="x", max_questions=0)
    with pytest.raises(ValidationError):
        ClarifyRequirementsInput(requirement="x", max_questions=21)


# --- Tool 2: generate_technical_proposal ----------------------------------


async def test_generate_proposal_ok():
    from hy3_architecture_mcp.schemas import (
        Architecture,
        GenerateTechnicalProposalOutput,
        NonFunctionalDesign,
    )

    out = GenerateTechnicalProposalOutput(
        title="KB",
        executive_overview="ov",
        architecture=Architecture(components=["c"], data_flow=["d"], interfaces=["i"]),
        technology_choices=[],
        alternatives=[],
        non_functional_design=NonFunctionalDesign(
            performance=[], reliability=[], observability=[], maintainability=[]
        ),
        risks=[],
        open_questions=[],
    )
    _runtime._client = FakeHy3Client([out])
    data = GenerateTechnicalProposalInput(requirements="need a KB", proposal_depth="detailed")
    result = await proposal.run(data)
    assert result.title == "KB"


def test_proposal_input_rejects_empty_requirements():
    with pytest.raises(ValidationError):
        GenerateTechnicalProposalInput(requirements="   ")


def test_proposal_input_rejects_bad_depth():
    with pytest.raises(ValidationError):
        GenerateTechnicalProposalInput(requirements="x", proposal_depth="huge")  # type: ignore[arg-type]


# --- Tool 3: review_technical_proposal ------------------------------------


async def test_review_ok():
    from hy3_architecture_mcp.schemas import ReviewTechnicalProposalOutput

    out = ReviewTechnicalProposalOutput(
        verdict="approve_with_changes",
        score=72,
        strengths=["s"],
        findings=[],
        missing_decisions=[],
        priority_actions=["a"],
    )
    _runtime._client = FakeHy3Client([out])
    data = ReviewTechnicalProposalInput(proposal="the proposal", risk_threshold="low")
    result = await review.run(data)
    assert result.score == 72


def test_review_input_rejects_empty_proposal():
    with pytest.raises(ValidationError):
        ReviewTechnicalProposalInput(proposal="")


def test_review_input_rejects_bad_risk_threshold():
    with pytest.raises(ValidationError):
        ReviewTechnicalProposalInput(proposal="x", risk_threshold="extreme")  # type: ignore[arg-type]


def test_review_score_range_enforced():
    from hy3_architecture_mcp.schemas import ReviewTechnicalProposalOutput

    with pytest.raises(ValidationError):
        ReviewTechnicalProposalOutput(
            verdict="approve",
            score=101,
            strengths=[],
            findings=[],
            missing_decisions=[],
            priority_actions=[],
        )
    with pytest.raises(ValidationError):
        ReviewTechnicalProposalOutput(
            verdict="approve",
            score=-1,
            strengths=[],
            findings=[],
            missing_decisions=[],
            priority_actions=[],
        )


# --- Tool 4: create_implementation_plan ----------------------------------


async def test_plan_ok():
    from hy3_architecture_mcp.schemas import (
        CreateImplementationPlanOutput,
        ImplementationTask,
        Milestone,
    )

    out = CreateImplementationPlanOutput(
        milestones=[
            Milestone(
                name="M1",
                goal="g",
                tasks=[
                    ImplementationTask(
                        id="T1",
                        title="t",
                        description="d",
                        dependencies=[],
                        suggested_role="dev",
                        estimated_effort="2d",
                        deliverables=["x"],
                        acceptance_criteria=["a"],
                    )
                ],
            )
        ],
        critical_path=["T1"],
        parallelizable_work=[],
        delivery_risks=[],
        definition_of_done=["done"],
    )
    _runtime._client = FakeHy3Client([out])
    data = CreateImplementationPlanInput(proposal="p", team_size=5, target_days=30)
    result = await planning.run(data)
    assert result.critical_path == ["T1"]


def test_plan_input_rejects_zero_team_size():
    with pytest.raises(ValidationError):
        CreateImplementationPlanInput(proposal="p", team_size=0)


def test_plan_input_rejects_bad_target_days():
    with pytest.raises(ValidationError):
        CreateImplementationPlanInput(proposal="p", team_size=1, target_days=0)


def test_plan_input_rejects_empty_proposal():
    with pytest.raises(ValidationError):
        CreateImplementationPlanInput(proposal="", team_size=1)


# --- Tool 5: analyze_project_context (structure; security in test_path_security) --


def test_analyze_input_rejects_empty_paths():
    with pytest.raises(ValidationError):
        AnalyzeProjectContextInput(paths=[])


def test_analyze_input_rejects_max_depth_out_of_range():
    with pytest.raises(ValidationError):
        AnalyzeProjectContextInput(paths=["."], max_depth=11)
    with pytest.raises(ValidationError):
        AnalyzeProjectContextInput(paths=["."], max_depth=-1)


# --- Client wiring: tools use the runtime singleton -----------------------


async def test_tool_propagates_hy3_error():
    from hy3_architecture_mcp.exceptions import Hy3APIError

    _runtime._client = FakeHy3Client([Hy3APIError("boom")])
    data = ClarifyRequirementsInput(requirement="x")
    with pytest.raises(Hy3APIError):
        await requirements.run(data)
