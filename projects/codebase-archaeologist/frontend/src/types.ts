// Shared TypeScript types mirroring the backend models

// ── Job status ───────────────────────────────────────────────
export type JobPhase =
  | 'pending'
  | 'ingesting'
  | 'graphing'
  | 'planning'
  | 'analyzing'
  | 'consistency_check'
  | 'synthesizing'
  | 'generating'
  | 'done'
  | 'failed';

export interface JobStatus {
  job_id: string;
  phase: JobPhase;
  progress_pct: number;
  current_batch: number;
  total_batches: number;
  current_files: string[];
  message: string;
  error: string;
  estimated_remaining_sec: number | null;
  result: ArchitectureReport | null;
  created_at: string;
  updated_at: string;
}

// ── Architecture Report ──────────────────────────────────────

export interface ArchOverview {
  architecture_style: string;
  language: string;
  framework: string;
  summary: string;
  reading_guide: string[];
}

export interface ModuleOverview {
  name: string;
  path: string;
  responsibility: string;
  exports: string[];
  depends_on: string[];
  depended_by: string[];
  stability: string;
}

export interface CallChain {
  name: string;
  sequence: string[];
  description: string;
}

export interface DesignPattern {
  pattern: string;
  location: string;
  appropriateness: string;
  note: string;
}

export interface Risk {
  severity: string;
  risk_type: string;
  location: string[];
  impact: string;
  fix_suggestion: string;
}

export interface ArchMetrics {
  total_modules: number;
  total_classes: number;
  avg_dependency_depth: number;
  god_class_candidates: string[];
  test_coverage_estimate: string;
}

export interface ArchitectureReport {
  overview: ArchOverview;
  modules: ModuleOverview[];
  call_chains: CallChain[];
  design_patterns: DesignPattern[];
  risks: Risk[];
  metrics: ArchMetrics;
  generated_at: string;
}

// ── QA ───────────────────────────────────────────────────────

export interface QAResponse {
  answer: string;
  sources: { path: string; score: number; type: string }[];
}
