import type { CoverageItem, Criterion } from "../types";


type CoverageMatrixProps = {
  coverage: CoverageItem[];
  criteria: Criterion[];
  onEvidenceSelect: (evidenceId: string) => void;
};

export default function CoverageMatrix({
  coverage,
  criteria,
  onEvidenceSelect,
}: CoverageMatrixProps) {
  const criteriaById = new Map(criteria.map((criterion) => [criterion.criterion_id, criterion]));

  return (
    <section className="report-section" aria-labelledby="coverage-heading">
      <div className="section-heading">
        <p className="eyebrow">验收矩阵</p>
        <h2 id="coverage-heading">验收覆盖</h2>
      </div>
      <div className="coverage-grid">
        {coverage.map((item) => {
          const criterion = criteriaById.get(item.criterion_id);
          const statusText =
            item.status === "covered"
              ? "已通过"
              : item.status === "violated"
                ? "未满足"
                : "待确认";
          const criterionLabel = criterion?.title ?? item.criterion_id;
          return (
            <article
              className={`coverage-card coverage-${item.status}`}
              key={item.criterion_id}
              aria-label={`${criterionLabel}：约束${statusText}`}
            >
              <div className="coverage-title">
                <span className="coverage-status" role="status" aria-label={statusText}>
                  {statusText}
                </span>
                <code>{item.criterion_id}</code>
              </div>
              <h3>{criterionLabel}</h3>
              <p>{item.explanation}</p>
              <div className="evidence-links">
                {item.evidence_ids.map((evidenceId) => (
                  <button
                    className="evidence-chip"
                    key={evidenceId}
                    onClick={() => onEvidenceSelect(evidenceId)}
                    type="button"
                    aria-label={`查看“${criterionLabel}”的证据 ${evidenceId}`}
                  >
                    {evidenceId}
                  </button>
                ))}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
