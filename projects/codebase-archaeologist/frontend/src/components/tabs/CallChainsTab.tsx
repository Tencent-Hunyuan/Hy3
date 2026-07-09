import { useState } from 'react';
import type { ArchitectureReport } from '../../types';

interface Props { report: ArchitectureReport; }

export function CallChainsTab({ report }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div className="space-y-3">
      {report.call_chains.map((chain) => {
        const isExpanded = expanded === chain.name;
        return (
          <div key={chain.name} className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden hover:shadow-md transition-shadow">
            <button
              onClick={() => setExpanded(isExpanded ? null : chain.name)}
              className="w-full text-left px-5 py-3.5 flex items-center justify-between"
            >
              <div className="flex-1 min-w-0">
                <h4 className="font-medium text-gray-800">{chain.name}</h4>
                <p className="text-xs text-gray-400 mt-1">
                  {chain.sequence.length} 步
                  {chain.description && ` · ${chain.description.slice(0, 80)}`}
                </p>
              </div>
              <span className="text-gray-400 ml-3">{isExpanded ? '▾' : '▸'}</span>
            </button>
            {isExpanded && (
              <div className="px-5 pb-4 border-t border-gray-100 pt-4">
                <p className="text-sm text-gray-600 mb-4">{chain.description}</p>
                <div className="space-y-1.5">
                  {chain.sequence.map((step, i) => (
                    <div key={i} className="flex items-center gap-3 group">
                      <span className="flex-shrink-0 w-6 h-6 rounded-md bg-indigo-50 text-indigo-600
                                     flex items-center justify-center text-xs font-medium border border-indigo-100">
                        {i + 1}
                      </span>
                      <code className="flex-1 px-3 py-1.5 bg-gray-50 rounded-lg text-sm font-mono text-gray-700
                                       group-hover:bg-gray-100 transition-colors border border-gray-100">
                        {step}
                      </code>
                      {i < chain.sequence.length - 1 && (
                        <span className="text-gray-300 text-lg">↓</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })}
      {report.call_chains.length === 0 && (
        <p className="text-center text-gray-400 py-10">未识别到关键调用链。</p>
      )}
    </div>
  );
}
