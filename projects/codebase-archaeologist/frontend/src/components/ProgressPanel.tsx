import type { JobStatus } from '../types';

const PHASE_LABELS: Record<string, string> = {
  pending: '等待中...',
  ingesting: '克隆仓库',
  graphing: '构建依赖图谱',
  planning: '规划分析策略',
  analyzing: 'ReAct 智能体分析中',
  consistency_check: '跨批次一致性校验',
  synthesizing: '综合研判生成报告',
  generating: '生成可视化产物',
  done: '分析完成',
  failed: '分析失败',
};

interface Props {
  status: JobStatus;
}

export function ProgressPanel({ status }: Props) {
  const phaseLabel = PHASE_LABELS[status.phase] || status.phase;
  const isRunning = !['done', 'failed'].includes(status.phase);
  const pct = status.progress_pct;

  const phases = [
    'ingesting',
    'graphing',
    'planning',
    'analyzing',
    'consistency_check',
    'synthesizing',
  ];
  const currentIndex = phases.indexOf(status.phase);

  return (
    <div className="max-w-2xl mx-auto mt-10">
      {/* 进度卡片 */}
      <div className="card-elevated p-6 glow">
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-semibold text-gray-800">分析进度</h3>
          {isRunning && (
            <span className="inline-flex items-center gap-2 text-sm text-indigo-600">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-indigo-500" />
              </span>
              运行中
            </span>
          )}
          {status.phase === 'done' && <span className="text-sm text-emerald-600">✅ 已完成</span>}
          {status.phase === 'failed' && <span className="text-sm text-red-500">❌ 失败</span>}
        </div>

        {/* 进度条 */}
        <div className="w-full bg-gray-100 rounded-full h-2.5 mb-4 overflow-hidden">
          <div
            className={`h-2.5 rounded-full transition-all duration-700 ease-out ${
              status.phase === 'failed' ? 'bg-red-400' : 'bg-gradient-to-r from-indigo-500 to-purple-500'
            }`}
            style={{ width: `${Math.max(pct, 2)}%` }}
          />
        </div>

        <p className="text-gray-700 font-medium">{phaseLabel}</p>
        <p className="text-sm text-gray-500 mt-1.5">{status.message}</p>

        {status.estimated_remaining_sec && status.estimated_remaining_sec > 0 && (
          <p className="text-xs text-gray-400 mt-2">
            预计剩余: ~{Math.ceil(status.estimated_remaining_sec / 60)} 分钟
          </p>
        )}
      </div>

      {/* 阶段列表 */}
      <div className="mt-4 bg-white rounded-xl border border-gray-100 shadow-sm p-5">
        <h4 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-4">管线阶段</h4>
        <div className="space-y-3">
          {phases.map((phase, idx) => {
            const done = idx < currentIndex;
            const active = idx === currentIndex;
            const pending = idx > currentIndex;

            return (
              <div key={phase} className="flex items-center gap-3 text-sm">
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs
                  ${done ? 'bg-emerald-100 text-emerald-600' : ''}
                  ${active ? 'bg-indigo-100 text-indigo-600 animate-pulse-dot' : ''}
                  ${pending ? 'bg-gray-50 text-gray-300' : ''}
                `}>
                  {done ? '✓' : active ? '●' : '○'}
                </span>
                <span className={
                  done ? 'text-emerald-700' :
                  active ? 'text-indigo-700 font-medium' :
                  'text-gray-400'
                }>
                  {PHASE_LABELS[phase]}
                </span>
                {active && status.current_batch > 0 && (
                  <span className="text-xs text-gray-400">
                    批次 {status.current_batch}/{status.total_batches || '?'}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
