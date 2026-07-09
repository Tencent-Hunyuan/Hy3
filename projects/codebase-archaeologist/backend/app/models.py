"""
Unified data models shared across the entire pipeline.

These are the canonical representations for FileManifest, DepGraph,
AnalysisPlan, BatchFindings, ArchitectureReport, etc.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Phase 1: Repo Ingest ─────────────────────────────────────

class FileTag(str, Enum):
    ENTRY_POINT = "entry_point"
    CONFIG = "config"
    CORE = "core"
    TEST = "test"
    DOCUMENTATION = "documentation"
    DEPRECATED = "deprecated"
    UNKNOWN = "unknown"


class FileInfo(BaseModel):
    path: str
    language: str = ""
    lines: int = 0
    estimated_tokens: int = 0
    tags: list[FileTag] = Field(default_factory=list)
    is_binary: bool = False
    is_third_party: bool = False


class FileManifest(BaseModel):
    repo_name: str = ""
    repo_url: str = ""
    local_path: str = ""
    language: str = ""
    framework: str = ""
    total_files: int = 0
    code_files: int = 0
    estimated_total_tokens: int = 0
    files: list[FileInfo] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)


# ── Phase 2: Dependency Graph ────────────────────────────────

class DepNode(BaseModel):
    path: str
    pagerank: float = 0.0
    in_degree: int = 0
    out_degree: int = 0
    module_type: str = "internal"  # internal | external | stdlib


class DepEdge(BaseModel):
    source: str
    target: str
    edge_type: str = "import"  # import | dynamic_import | lazy_load


class CycleInfo(BaseModel):
    nodes: list[str]
    length: int


class DepGraph(BaseModel):
    nodes: list[DepNode] = Field(default_factory=list)
    edges: list[DepEdge] = Field(default_factory=list)
    core_modules: list[DepNode] = Field(default_factory=list)
    entry_points: list[str] = Field(default_factory=list)
    cycles: list[CycleInfo] = Field(default_factory=list)
    orphans: list[str] = Field(default_factory=list)
    config_files: list[str] = Field(default_factory=list)


# ── Phase 2.5: Analysis Plan ─────────────────────────────────

class BatchPlan(BaseModel):
    id: int
    priority: str = "medium"  # highest | high | medium | low
    files: list[str]
    rationale: str = ""
    estimated_tokens: int = 0
    depends_on: list[int] = Field(default_factory=list)


class AnalysisPlan(BaseModel):
    strategy: str = ""
    focus_dimensions: list[str] = Field(default_factory=list)
    batches: list[BatchPlan] = Field(default_factory=list)
    special_instructions: str = ""


# ── Phase 3: Batch Findings ──────────────────────────────────

class ModuleRole(BaseModel):
    path: str = ""
    responsibility: str = ""
    stability: str = "medium"
    model_config = {"extra": "ignore"}


class KeyAbstraction(BaseModel):
    name: str
    kind: str = ""  # class | function | interface | decorator
    location: str = ""  # file:line
    role: str = ""


class DataFlow(BaseModel):
    description: str
    path: list[str] = Field(default_factory=list)


class DesignPattern(BaseModel):
    pattern: str
    location: str = ""
    appropriateness: str = "appropriate"  # appropriate | questionable | inappropriate
    note: str = ""


class Risk(BaseModel):
    severity: str = "medium"
    risk_type: str = ""
    location: str | list[str] = ""
    impact: str = ""
    fix_suggestion: str = ""
    model_config = {"extra": "ignore"}

    def to_list_location(self) -> list[str]:
        if isinstance(self.location, list):
            return self.location
        return [self.location] if self.location else []


class BatchFinding(BaseModel):
    batch_id: int
    files_analyzed: list[str] = Field(default_factory=list)
    module_roles: list[ModuleRole] = Field(default_factory=list)
    key_abstractions: list[KeyAbstraction] = Field(default_factory=list)
    data_flows: list[DataFlow] = Field(default_factory=list)
    design_patterns: list[DesignPattern] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    clues_for_next: str = ""
    # Allow extra fields from Hy3 output to avoid validation errors
    model_config = {"extra": "ignore"}


# ── Phase 3.5: Consistency Check ─────────────────────────────

class HardConflict(BaseModel):
    batch_a: int
    batch_b: int
    claim_a: str
    claim_b: str
    resolution: str
    confidence: float = 0.5


class ConsistencyReport(BaseModel):
    hard_conflicts: list[HardConflict] = Field(default_factory=list)
    perspective_diffs: list[dict[str, Any]] = Field(default_factory=list)
    override_instructions: str = ""


# ── Phase 4: Architecture Report ─────────────────────────────

class ModuleOverview(BaseModel):
    name: str
    path: str = ""
    responsibility: str = ""
    exports: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    depended_by: list[str] = Field(default_factory=list)
    stability: str = "medium"


class CallChain(BaseModel):
    name: str
    sequence: list[str] = Field(default_factory=list)
    description: str = ""


class ArchOverview(BaseModel):
    architecture_style: str = ""
    language: str = ""
    framework: str = ""
    summary: str = ""
    reading_guide: list[str] = Field(default_factory=list)


class ArchMetrics(BaseModel):
    total_modules: int = 0
    total_classes: int = 0
    avg_dependency_depth: float = 0.0
    god_class_candidates: list[str] = Field(default_factory=list)
    test_coverage_estimate: str = "N/A"


class ArchitectureReport(BaseModel):
    overview: ArchOverview = Field(default_factory=ArchOverview)
    modules: list[ModuleOverview] = Field(default_factory=list)
    call_chains: list[CallChain] = Field(default_factory=list)
    design_patterns: list[DesignPattern] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    metrics: ArchMetrics = Field(default_factory=ArchMetrics)
    generated_at: datetime = Field(default_factory=datetime.now)


# ── PR Impact Analysis (Demo 2) ──────────────────────────────

class PRImpactItem(BaseModel):
    severity: str = "medium"  # critical | high | medium | low
    module: str = ""
    impact_scope: str = ""
    affected_dependents: list[str] = Field(default_factory=list)
    old_call_chain: list[str] = Field(default_factory=list)
    new_call_chain: list[str] = Field(default_factory=list)
    ai_analysis: str = ""


class PRImpactReport(BaseModel):
    pr_number: int = 0
    pr_title: str = ""
    changed_files: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    impacts: list[PRImpactItem] = Field(default_factory=list)
    review_order: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.now)


# ── Job management ───────────────────────────────────────────

class JobPhase(str, Enum):
    PENDING = "pending"
    INGESTING = "ingesting"
    GRAPHING = "graphing"
    PLANNING = "planning"
    ANALYZING = "analyzing"
    CONSISTENCY_CHECK = "consistency_check"
    SYNTHESIZING = "synthesizing"
    GENERATING = "generating"
    DONE = "done"
    FAILED = "failed"


class JobStatus(BaseModel):
    job_id: str
    phase: JobPhase = JobPhase.PENDING
    progress_pct: int = 0
    current_batch: int = 0
    total_batches: int = 0
    current_files: list[str] = Field(default_factory=list)
    message: str = ""
    error: str = ""
    estimated_remaining_sec: int | None = None
    result: ArchitectureReport | PRImpactReport | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
