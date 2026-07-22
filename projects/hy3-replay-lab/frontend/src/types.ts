export type FixtureSummary = {
  fixture_id: string;
  title: string;
  description: string;
  domain: string;
};

export type HealthResponse = {
  status: "ok";
  live_provider_configured: boolean;
};

export type AnalysisProvider = "fake" | "hy3";

export type Criterion = {
  criterion_id: string;
  title: string;
  description: string;
  priority: "must" | "should" | "could";
};

export type TraceStep = {
  step_id: string;
  sequence: number;
  kind:
    | "observation"
    | "decision"
    | "tool_call"
    | "tool_result"
    | "action"
    | "validation"
    | "claim";
  summary: string;
  details: string;
  status: "ok" | "warning" | "failed" | "unknown";
  criterion_ids: string[];
  evidence_ids: string[];
};

export type Evidence = {
  evidence_id: string;
  step_id: string;
  kind:
    | "requirement"
    | "tool_output"
    | "test_result"
    | "source_excerpt"
    | "artifact"
    | "note";
  source_label: string;
  content: string;
};

export type TaskSpec = {
  schema_version: "1.0";
  fixture_id: string | null;
  task: {
    title: string;
    description: string;
  };
  criteria: Criterion[];
  trace: TraceStep[];
  evidence: Evidence[];
};

export type CoverageItem = {
  criterion_id: string;
  status: "covered" | "violated" | "unknown";
  supporting_step_ids: string[];
  evidence_ids: string[];
  explanation: string;
};

export type ValidationGate = {
  description: string;
  criterion_ids: string[];
  evidence_ids: string[];
};

export type ReplayAction = {
  order: number;
  action: string;
  evidence_ids: string[];
  validation_gate: ValidationGate;
};

export type ReplayReport = {
  schema_version: "1.0";
  report_id: string;
  fixture_id: string | null;
  task: {
    title: string;
    description: string;
  };
  criteria: Criterion[];
  timeline: TraceStep[];
  evidence: Evidence[];
  coverage: CoverageItem[];
  finding: {
    severity: "low" | "medium" | "high" | "critical";
    category: string;
    first_divergence_step_id: string | null;
    impact_step_ids: string[];
    explanation: string;
    evidence_ids: string[];
    hypotheses: string[];
  };
  replay_plan: {
    preserved_step_ids: string[];
    rerun_from_step_id: string | null;
    rerun_step_ids: string[];
    actions: ReplayAction[];
    stop_conditions: ValidationGate[];
    prohibited_actions: Array<{
      action: string;
      reason: string;
      evidence_ids: string[];
    }>;
  };
  metadata: {
    provider: string;
    model: string;
    mode: "fake" | "live";
    latency_ms: number | null;
    prompt_tokens: number | null;
    completion_tokens: number | null;
    total_tokens: number | null;
    request_attempts: number | null;
  };
};

export type AnalysisResponse = {
  report: ReplayReport;
  exports: {
    json: string;
    markdown: string;
  };
};
