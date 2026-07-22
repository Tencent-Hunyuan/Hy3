import type { TraceStep } from "../types";


const KIND_LABELS: Record<TraceStep["kind"], string> = {
  observation: "观察",
  decision: "决策",
  tool_call: "工具调用",
  tool_result: "工具结果",
  action: "操作",
  validation: "验证",
  claim: "结论",
};


type TimelineProps = {
  steps: TraceStep[];
  firstDivergenceStepId: string | null;
  impactStepIds: string[];
  onEvidenceSelect: (evidenceId: string) => void;
};

export default function Timeline({
  steps,
  firstDivergenceStepId,
  impactStepIds,
  onEvidenceSelect,
}: TimelineProps) {
  const impactIds = new Set(impactStepIds);

  return (
    <section className="panel timeline-panel" aria-labelledby="timeline-heading">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">执行轨迹</p>
          <h2 id="timeline-heading">标准化时间线</h2>
        </div>
        <span className="panel-count">{steps.length} 个步骤</span>
      </div>

      <ol className="timeline" aria-label="标准化智能体轨迹">
        {steps.map((step) => {
          const isDivergence = step.step_id === firstDivergenceStepId;
          const isImpact = impactIds.has(step.step_id);
          return (
            <li
              className={`timeline-step status-${step.status}${
                isDivergence ? " is-divergence" : ""
              }${isImpact ? " is-impact" : ""}`}
              data-divergence={isDivergence ? "true" : "false"}
              data-testid={`timeline-step-${step.step_id}`}
              key={step.step_id}
            >
              <div className="step-rail" aria-hidden="true">
                <span>{String(step.sequence).padStart(2, "0")}</span>
              </div>
              <article>
                <div className="step-meta">
                  <span>{KIND_LABELS[step.kind]}</span>
                  <code>{step.step_id}</code>
                  {isDivergence && <strong>首个偏航点</strong>}
                  {isImpact && <strong className="impact-label">下游影响</strong>}
                </div>
                <h3>{step.summary}</h3>
                <p>{step.details}</p>
                {step.evidence_ids.length > 0 && (
                  <div className="evidence-links" aria-label={`${step.step_id} 的证据`}>
                    {step.evidence_ids.map((evidenceId) => (
                      <button
                        className="evidence-chip"
                        key={evidenceId}
                        onClick={() => onEvidenceSelect(evidenceId)}
                        type="button"
                      >
                        {evidenceId}
                      </button>
                    ))}
                  </div>
                )}
              </article>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
