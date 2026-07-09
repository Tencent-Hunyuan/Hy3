import { useEffect, useState } from 'react';
import type { ArchitectureReport } from '../../types';
import { getJobStatus } from '../../api';

interface Props { report: ArchitectureReport; jobId: string; }

interface TokenUsage {
  calls: number;
  prompt_tokens: number;
  completion_tokens: number;
  cache_read_tokens: number;
  total_cost_yuan: number;
  latency_ms: number;
}

function fmt(n: number | undefined): string {
  if (n === undefined || n === null) return '—';
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export function OverviewTab({ report, jobId }: Props) {
  const { overview, metrics } = report;
  const [usage, setUsage] = useState<TokenUsage | null>(null);

  useEffect(() => {
    fetch(`/api/jobs/${jobId}/usage`)
      .then((r) => r.json())
      .then((data) => {
        if (data.calls !== undefined) setUsage(data);
      })
      .catch(() => {});
  }, [jobId]);

  const cards = [
    { label: '模块数', value: metrics.total_modules },
    { label: '类数量', value: metrics.total_classes },
    { label: '平均依赖深度', value: metrics.avg_dependency_depth.toFixed(1) },
    { label: '架构风格', value: overview.architecture_style },
  ];

  return (
    <div className="space-y-6">
      {/* 摘要 */}
      <div className="card-elevated p-6 glow">
        <h3 className="text-lg font-semibold text-gray-800 mb-3">架构摘要</h3>
        <p className="text-gray-600 leading-relaxed">{overview.summary}</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <span className="px-3 py-1 bg-indigo-50 text-indigo-600 text-xs font-medium rounded-full border border-indigo-100">
            {overview.language}
          </span>
          <span className="px-3 py-1 bg-emerald-50 text-emerald-600 text-xs font-medium rounded-full border border-emerald-100">
            {overview.framework}
          </span>
          <span className="px-3 py-1 bg-purple-50 text-purple-600 text-xs font-medium rounded-full border border-purple-100">
            {overview.architecture_style}
          </span>
        </div>
      </div>

      {/* 指标卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {cards.map((c) => (
          <div key={c.label} className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 hover:shadow-md transition-shadow">
            <div className="text-xs text-gray-400 uppercase tracking-wider">{c.label}</div>
            <div className="mt-2 text-2xl font-bold text-gray-900">{c.value}</div>
          </div>
        ))}
      </div>

      {/* Token 用量 */}
      {usage && usage.calls > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-xs font-medium text-gray-400 uppercase tracking-wider">Hy3 Token 用量</h4>
            <span className="text-xs text-emerald-600 font-medium">
              ≈ ¥{usage.total_cost_yuan.toFixed(4)}
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
            <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
              <div className="text-lg font-bold text-gray-700">{usage.calls}</div>
              <div className="text-[11px] text-gray-400 mt-0.5">API 调用</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
              <div className="text-lg font-bold text-indigo-600">{fmt(usage.prompt_tokens)}</div>
              <div className="text-[11px] text-gray-400 mt-0.5">输入 Token</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
              <div className="text-lg font-bold text-purple-600">{fmt(usage.completion_tokens)}</div>
              <div className="text-[11px] text-gray-400 mt-0.5">输出 Token</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
              <div className="text-lg font-bold text-emerald-600">{fmt(usage.cache_read_tokens)}</div>
              <div className="text-[11px] text-gray-400 mt-0.5">缓存命中</div>
            </div>
          </div>
          <div className="mt-3 text-xs text-gray-400 text-center">
            {(usage.latency_ms / 1000).toFixed(1)}s 总耗时
          </div>
        </div>
      )}

      {/* 阅读指南 */}
      {overview.reading_guide && overview.reading_guide.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">📖 阅读指南</h3>
          <ol className="space-y-3">
            {overview.reading_guide.map((step, i) => (
              <li key={i} className="flex gap-3 text-gray-600 text-sm">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-indigo-50 text-indigo-600
                               flex items-center justify-center text-xs font-medium border border-indigo-100">
                  {i + 1}
                </span>
                <span className="pt-0.5">{step}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* God Class 候选 */}
      {metrics.god_class_candidates && metrics.god_class_candidates.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
          <h4 className="text-sm font-semibold text-amber-700 mb-2">上帝类候选</h4>
          <ul className="space-y-1">
            {metrics.god_class_candidates.map((c, i) => (
              <li key={i} className="text-sm text-amber-600 font-mono">{c}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
