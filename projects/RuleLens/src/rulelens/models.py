"""RuleLens 数据模型（Pydantic v2）。

字段名固定为英文，UI 文案使用中文。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# 枚举
# --------------------------------------------------------------------------- #
class RuleType(str, Enum):
    ELIGIBILITY = "ELIGIBILITY"
    OBLIGATION = "OBLIGATION"
    PROHIBITION = "PROHIBITION"
    DEADLINE = "DEADLINE"
    THRESHOLD = "THRESHOLD"
    EXCEPTION = "EXCEPTION"
    CONSEQUENCE = "CONSEQUENCE"
    DEFINITION = "DEFINITION"
    PRIORITY = "PRIORITY"
    OTHER = "OTHER"


class Verdict(str, Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    INSUFFICIENT_INFO = "INSUFFICIENT_INFO"


class CitationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    SOURCE_ONLY = "SOURCE_ONLY"
    FAILED = "FAILED"


class IssueType(str, Enum):
    AMBIGUOUS_TERM = "AMBIGUOUS_TERM"
    CONFLICT = "CONFLICT"
    MISSING_BOUNDARY = "MISSING_BOUNDARY"
    MISSING_PROCEDURE = "MISSING_PROCEDURE"
    MISSING_EXCEPTION = "MISSING_EXCEPTION"
    UNVERIFIABLE = "UNVERIFIABLE"
    REDUNDANT = "REDUNDANT"


# --------------------------------------------------------------------------- #
# 来源与引用
# --------------------------------------------------------------------------- #
class SourceBlock(BaseModel):
    """一段可被引用的来源文本。"""

    source_id: str
    page_number: int | None = None
    text: str
    char_start: int
    char_end: int


class Citation(BaseModel):
    """模型对某条来源块的引用。status 由本地核验后填充。"""

    source_id: str
    evidence_quote: str = ""
    status: CitationStatus | None = None


# --------------------------------------------------------------------------- #
# 规则
# --------------------------------------------------------------------------- #
class Rule(BaseModel):
    rule_id: str
    title: str
    normalized_statement: str
    rule_type: RuleType
    topic: str
    conditions: list[str] = Field(default_factory=list)
    exceptions: list[str] = Field(default_factory=list)
    consequences: list[str] = Field(default_factory=list)
    related_rule_ids: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


class RuleExtractionResult(BaseModel):
    document_title: str
    document_summary: str
    defined_terms: dict[str, str] = Field(default_factory=dict)
    rules: list[Rule]


# --------------------------------------------------------------------------- #
# 情景
# --------------------------------------------------------------------------- #
class Scenario(BaseModel):
    scenario_id: str
    title: str
    description: str
    boundary_type: str
    difficulty: str
    related_rule_ids: list[str] = Field(min_length=1)
    required_facts: list[str] = Field(default_factory=list)


class ScenarioSet(BaseModel):
    scenarios: list[Scenario] = Field(min_length=6, max_length=12)


# --------------------------------------------------------------------------- #
# 裁决
# --------------------------------------------------------------------------- #
class Judgment(BaseModel):
    scenario_id: str
    verdict: Verdict
    rationale_summary: str = Field(max_length=500)
    applied_rule_ids: list[str]
    citations: list[Citation] = Field(min_length=1)
    missing_information: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


# --------------------------------------------------------------------------- #
# 歧义
# --------------------------------------------------------------------------- #
class AmbiguityIssue(BaseModel):
    issue_id: str
    issue_type: IssueType
    title: str
    description: str
    impact: str
    suggestion: str
    severity: str
    citations: list[Citation]
    confidence: float = Field(ge=0, le=1)


class AmbiguityReport(BaseModel):
    issues: list[AmbiguityIssue]


# --------------------------------------------------------------------------- #
# 答题与聚合
# --------------------------------------------------------------------------- #
class QuizAttempt(BaseModel):
    scenario_id: str
    user_verdict: Verdict
    judgment: Judgment
    is_correct: bool
    answered_at: datetime


class AnalysisBundle(BaseModel):
    schema_version: str = "1.0"
    file_name: str
    file_sha256: str
    analyzed_at: datetime
    model_name: str
    sources: list[SourceBlock]
    rule_result: RuleExtractionResult
    scenario_set: ScenarioSet
    ambiguity_report: AmbiguityReport
    attempts: list[QuizAttempt] = Field(default_factory=list)
