"""Pydantic input/output schemas for every MCP tool.

Each tool has an ``...Input`` model (used as the MCP tool input schema) and a
matching ``...Output`` model that is validated from Hy3's JSON output.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _require_non_empty(v: str) -> str:
    """Reject empty or whitespace-only required text."""
    if v is None or not v.strip():
        raise ValueError("must not be empty or whitespace-only")
    return v


class _Base(BaseModel):
    model_config = {"extra": "forbid"}


# ===========================================================================
# Tool 1 - clarify_requirements
# ===========================================================================


class ClarifyRequirementsInput(_Base):
    requirement: str = Field(..., min_length=1, description="原始模糊需求")
    project_context: str | None = Field(None, description="可选的项目背景，帮助聚焦澄清问题")
    constraints: list[str] = Field(default_factory=list, description="已知约束")
    output_language: str = Field("zh-CN", description="输出语言，例如 zh-CN / en")
    max_questions: int = Field(8, ge=1, le=20, description="澄清问题数量上限 1~20")

    _validate_requirement = field_validator("requirement")(_require_non_empty)


class ClarifyRequirementsOutput(_Base):
    understood_goals: list[str]
    ambiguities: list[str]
    missing_information: list[str]
    clarifying_questions: list[str]
    acceptance_criteria: list[str]
    assumptions: list[str]


# ===========================================================================
# Tool 2 - generate_technical_proposal
# ===========================================================================

ProposalDepth = Literal["brief", "standard", "detailed"]


class Architecture(_Base):
    components: list[str]
    data_flow: list[str]
    interfaces: list[str]


class TechnologyChoice(_Base):
    name: str
    rationale: str


class Alternative(_Base):
    name: str
    description: str
    tradeoffs: str


class NonFunctionalDesign(_Base):
    performance: list[str]
    reliability: list[str]
    observability: list[str]
    maintainability: list[str]


class ProposalRisk(_Base):
    description: str
    severity: Literal["low", "medium", "high"]
    mitigation: str


class GenerateTechnicalProposalInput(_Base):
    requirements: str = Field(..., min_length=1, description="已澄清的需求")
    project_context: str | None = None
    preferred_stack: list[str] = Field(default_factory=list, description="倾向的技术栈")
    constraints: list[str] = Field(default_factory=list)
    proposal_depth: ProposalDepth = "standard"
    output_language: str = "zh-CN"

    _validate_requirements = field_validator("requirements")(_require_non_empty)


class GenerateTechnicalProposalOutput(_Base):
    title: str
    executive_overview: str
    architecture: Architecture
    technology_choices: list[TechnologyChoice]
    alternatives: list[Alternative]
    non_functional_design: NonFunctionalDesign
    risks: list[ProposalRisk]
    open_questions: list[str]


# ===========================================================================
# Tool 3 - review_technical_proposal
# ===========================================================================

DEFAULT_REVIEW_DIMENSIONS = [
    "requirement_coverage",
    "maintainability",
    "scalability",
    "reliability",
    "cost",
    "testability",
    "observability",
    "data_privacy",
]

RiskThreshold = Literal["low", "medium", "high"]
Verdict = Literal["approve", "approve_with_changes", "reject"]
Severity = Literal["low", "medium", "high", "critical"]


class ReviewTechnicalProposalInput(_Base):
    proposal: str = Field(..., min_length=1, description="待评审的技术方案文本")
    requirements: str | None = Field(None, description="原始需求，用于覆盖度检查")
    review_dimensions: list[str] = Field(
        default_factory=lambda: list(DEFAULT_REVIEW_DIMENSIONS),
        description="评审维度，留空使用默认 8 个维度",
    )
    risk_threshold: RiskThreshold = "medium"
    output_language: str = "zh-CN"

    _validate_proposal = field_validator("proposal")(_require_non_empty)


class ReviewFinding(_Base):
    id: str
    severity: Severity
    dimension: str
    evidence: str
    impact: str
    recommendation: str


class ReviewTechnicalProposalOutput(_Base):
    verdict: Verdict
    score: int = Field(..., ge=0, le=100)
    strengths: list[str]
    findings: list[ReviewFinding]
    missing_decisions: list[str]
    priority_actions: list[str]


# ===========================================================================
# Tool 4 - create_implementation_plan
# ===========================================================================


class ImplementationTask(_Base):
    id: str
    title: str
    description: str
    dependencies: list[str]
    suggested_role: str
    estimated_effort: str
    deliverables: list[str]
    acceptance_criteria: list[str]


class Milestone(_Base):
    name: str
    goal: str
    tasks: list[ImplementationTask]


class CreateImplementationPlanInput(_Base):
    proposal: str = Field(..., min_length=1, description="已通过评审的技术方案")
    team_size: int = Field(..., ge=1, description="团队人数")
    target_days: int | None = Field(None, ge=1, description="目标交付天数")
    available_roles: list[str] = Field(default_factory=list, description="可承担的角色")
    output_language: str = "zh-CN"

    _validate_proposal = field_validator("proposal")(_require_non_empty)


class CreateImplementationPlanOutput(_Base):
    milestones: list[Milestone]
    critical_path: list[str]
    parallelizable_work: list[str]
    delivery_risks: list[str]
    definition_of_done: list[str]


# ===========================================================================
# Tool 5 - analyze_project_context
# ===========================================================================


class AnalyzeProjectContextInput(_Base):
    paths: list[str] = Field(..., min_length=1, description="要分析的文件或目录")
    include_content_summary: bool = True
    max_depth: int = Field(2, ge=0, le=10, description="目录递归深度 0~10")
    output_language: str = "zh-CN"


class AnalyzeProjectContextOutput(_Base):
    detected_stack: list[str]
    project_structure: list[str]
    important_files: list[str]
    constraints: list[str]
    architecture_observations: list[str]
    warnings: list[str]


# A registry used by tests/CLI introspection.
TOOL_OUTPUT_MODELS = {
    "clarify_requirements": ClarifyRequirementsOutput,
    "generate_technical_proposal": GenerateTechnicalProposalOutput,
    "review_technical_proposal": ReviewTechnicalProposalOutput,
    "create_implementation_plan": CreateImplementationPlanOutput,
    "analyze_project_context": AnalyzeProjectContextOutput,
}
