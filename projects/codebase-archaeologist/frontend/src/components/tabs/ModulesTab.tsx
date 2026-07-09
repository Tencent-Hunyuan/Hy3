import { useState } from 'react';
import type { ArchitectureReport } from '../../types';

interface Props { report: ArchitectureReport; }

const STABILITY: Record<string, string> = {
  high: 'bg-emerald-50 text-emerald-600 border-emerald-200',
  medium: 'bg-amber-50 text-amber-600 border-amber-200',
  low: 'bg-orange-50 text-orange-600 border-orange-200',
  volatile: 'bg-red-50 text-red-500 border-red-200',
};

export function ModulesTab({ report }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  const filtered = report.modules.filter((m) =>
    !search || `${m.name} ${m.path} ${m.responsibility}`.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-4">
      <div className="relative">
        <svg className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="搜索模块..."
          className="w-full pl-10 pr-4 py-2.5 bg-white border border-gray-200 rounded-xl
                   text-sm text-gray-700 placeholder-gray-400 input-focus transition-all"
        />
      </div>

      <div className="space-y-2">
        {filtered.map((mod) => {
          const isExpanded = expanded === mod.path;
          const stable = STABILITY[mod.stability] || 'bg-gray-50 text-gray-500 border-gray-200';
          return (
            <div key={mod.path} className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden hover:shadow-md transition-shadow">
              <button
                onClick={() => setExpanded(isExpanded ? null : mod.path)}
                className="w-full text-left px-5 py-3.5 flex items-center justify-between"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3">
                    <span className="font-medium text-gray-800 truncate">{mod.name}</span>
                    <span className={`px-2 py-0.5 rounded text-[11px] font-medium border ${stable}`}>
                      {mod.stability === 'high' ? '高稳定' : mod.stability === 'medium' ? '中稳定' : mod.stability === 'low' ? '低稳定' : mod.stability}
                    </span>
                  </div>
                  <div className="text-xs text-gray-400 font-mono mt-1">{mod.path}</div>
                </div>
                <span className="text-gray-400 ml-3">{isExpanded ? '▾' : '▸'}</span>
              </button>

              {isExpanded && (
                <div className="px-5 pb-4 border-t border-gray-100 pt-4 space-y-4">
                  <div>
                    <h4 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">职责</h4>
                    <p className="text-sm text-gray-600 mt-1">{mod.responsibility}</p>
                  </div>
                  {mod.exports.length > 0 && (
                    <div>
                      <h4 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">对外接口</h4>
                      <div className="flex flex-wrap gap-1.5 mt-1.5">
                        {mod.exports.map((exp) => (
                          <code key={exp} className="px-2 py-0.5 bg-gray-50 text-gray-600 rounded text-xs border border-gray-100">
                            {exp}
                          </code>
                        ))}
                      </div>
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <h4 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">依赖</h4>
                      {mod.depends_on.slice(0, 5).map((d) => (
                        <div key={d} className="text-xs text-gray-500 font-mono mt-1">{d}</div>
                      ))}
                      {mod.depends_on.length > 5 && <div className="text-xs text-gray-400">+{mod.depends_on.length - 5} 更多</div>}
                    </div>
                    <div>
                      <h4 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">被依赖</h4>
                      {mod.depended_by.slice(0, 5).map((d) => (
                        <div key={d} className="text-xs text-gray-500 font-mono mt-1">{d}</div>
                      ))}
                      {mod.depended_by.length > 5 && <div className="text-xs text-gray-400">+{mod.depended_by.length - 5} 更多</div>}
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {filtered.length === 0 && (
        <p className="text-center text-gray-400 py-10">未找到匹配的模块。</p>
      )}
    </div>
  );
}
