import type { ReplayReport } from "../types";


type ReplayPlanPanelProps = {
  report: ReplayReport;
  onEvidenceSelect: (evidenceId: string) => void;
};

export default function ReplayPlanPanel({ report, onEvidenceSelect }: ReplayPlanPanelProps) {
  const plan = report.replay_plan;

  return (
    <section className="report-section replay-section" aria-labelledby="replay-heading">
      <div className="section-heading split-heading">
        <div>
          <p className="eyebrow">最小重放</p>
          <h2 id="replay-heading">重放计划</h2>
        </div>
        <div className="rerun-origin">
          <span>从这里重启</span>
          <code>{plan.rerun_from_step_id ?? "无需重放"}</code>
        </div>
      </div>

      <ol className="replay-actions">
        {plan.actions.map((action) => (
          <li key={action.order}>
            <span className="action-order">{String(action.order).padStart(2, "0")}</span>
            <div>
              <h3>{action.action}</h3>
              <div className="validation-gate">
                <span>验证闸门</span>
                <p>{action.validation_gate.description}</p>
              </div>
              <div className="evidence-links">
                {action.evidence_ids.map((evidenceId) => (
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
            </div>
          </li>
        ))}
      </ol>

      <div className="replay-guardrails">
        <div>
          <h3>停止条件</h3>
          <ul>
            {plan.stop_conditions.map((condition) => (
              <li key={condition.description}>{condition.description}</li>
            ))}
          </ul>
        </div>
        <div className="prohibited-list">
          <h3>禁止操作</h3>
          <ul>
            {plan.prohibited_actions.map((item) => (
              <li key={item.action}>
                <strong>{item.action}</strong>
                <span>{item.reason}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
