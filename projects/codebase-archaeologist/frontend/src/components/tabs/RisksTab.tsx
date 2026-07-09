import { useState } from 'react';
import type { ArchitectureReport, Risk } from '../../types';

interface Props { report: ArchitectureReport; }

const SEV_CLASSES: Record<string, string> = {
  critical: 'border-red-200 bg-red-50/50',
  high: 'border-orange-200 bg-orange-50/50',
  medium: 'border-amber-200 bg-amber-50/50',
  low: 'border-gray-100 bg-white',
};

const SEV_BADGE: Record<string, string> = {
  critical: 'bg-red-100 text-red-600 border-red-200',
  high: 'bg-orange-100 text-orange-600 border-orange-200',
  medium: 'bg-amber-100 text-amber-600 border-amber-200',
  low: 'bg-gray-100 text-gray-500 border-gray-200',
};

const SEV_LABEL: Record<string, string> = {
  critical: '严重', high: '高危', medium: '中等', low: '低',
};

function RiskCard({ risk }: { risk: Risk }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={`rounded-xl border ${SEV_CLASSES[risk.severity] || 'border-gray-100'} p-4`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1.5">
            <span className={`px-2 py-0.5 rounded text-[11px] font-medium border ${SEV_BADGE[risk.severity]}`}>
              {SEV_LABEL[risk.severity] || risk.severity}
            </span>
            <span className="font-medium text-gray-700 text-sm">{risk.risk_type}</span>
          </div>
          <div className="text-xs text-gray-400 font-mono space-y-0.5 mt-1.5">
            {(Array.isArray(risk.location) ? risk.location : [risk.location]).slice(0, 3).map((loc, i) => (
              <div key={i}>{String(loc)}</div>
            ))}
          </div>
        </div>
        <button onClick={() => setExpanded(!expanded)} className="text-xs text-gray-400 hover:text-gray-600 ml-3">
          {expanded ? '收起' : '展开'}
        </button>
      </div>
      {expanded && (
        <div className="mt-4 pt-3 border-t border-gray-100 space-y-3">
          {risk.impact && (
            <div>
              <h4 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">影响范围</h4>
              <p className="text-sm text-gray-600 mt-1">{risk.impact}</p>
            </div>
          )}
          {risk.fix_suggestion && (
            <div>
              <h4 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">修复建议</h4>
              <p className="text-sm text-gray-600 mt-1">{risk.fix_suggestion}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function RisksTab({ report }: Props) {
  const [filter, setFilter] = useState<string>('all');
  const filtered = filter === 'all' ? report.risks : report.risks.filter((r) => r.severity === filter);
  const counts: Record<string, number> = {};
  report.risks.forEach((r) => { counts[r.severity] = (counts[r.severity] || 0) + 1; });

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        {[
          ['all', '全部'],
          ['critical', '严重'],
          ['high', '高危'],
          ['medium', '中等'],
          ['low', '低'],
        ].map(([sev, label]) => (
          <button
            key={sev}
            onClick={() => setFilter(sev)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all border
              ${filter === sev
                ? 'bg-indigo-50 text-indigo-600 border-indigo-200'
                : 'bg-white text-gray-500 border-gray-200 hover:border-gray-300'
              }
            `}
          >
            {label}
            {sev !== 'all' && counts[sev] ? ` ${counts[sev]}` : ''}
            {sev === 'all' ? ` ${report.risks.length}` : ''}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        {filtered.map((risk, i) => <RiskCard key={i} risk={risk} />)}
      </div>

      {filtered.length === 0 && (
        <p className="text-center text-gray-400 py-10">
          未发现{filter !== 'all' ? '该级别的' : ''}风险。
        </p>
      )}

      {/* 设计模式 */}
      {report.design_patterns.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 mt-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">设计模式</h3>
          <div className="space-y-3">
            {report.design_patterns.map((dp, i) => (
              <div key={i} className="flex items-start gap-3 text-sm">
                <span className="mt-0.5">{dp.appropriateness === 'appropriate' ? '✅' : '⚠️'}</span>
                <div>
                  <span className="font-medium text-gray-700">{dp.pattern}</span>
                  <span className="text-gray-400 ml-2">@{dp.location}</span>
                  {dp.note && <p className="text-gray-500 mt-1">{dp.note}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
