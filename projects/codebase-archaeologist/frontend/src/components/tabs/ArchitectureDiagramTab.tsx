import { useEffect, useRef } from 'react';
import type { ArchitectureReport } from '../../types';

declare const mermaid: any;

interface Props { report: ArchitectureReport; }

function shortName(path: string): string {
  const parts = path.replace(/\\/g, '/').split('/');
  return parts[parts.length - 1] || path;
}

export function ArchitectureDiagramTab({ report }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const diagram = buildArchitectureDiagram(report);
    renderMermaid(containerRef.current, diagram);
  }, [report]);

  // Compute layer assignment for visualization context
  const entryModules = report.modules.filter(m => m.depended_by.length >= 2 && m.depends_on.length <= 1);
  const leafModules = report.modules.filter(m => m.depends_on.length >= 2 && m.depended_by.length <= 0);

  return (
    <div className="space-y-6">
      {/* Mermaid diagram card */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 glow">
        <h3 className="text-lg font-semibold text-gray-800 mb-1">仓库架构全景图</h3>
        <p className="text-sm text-gray-400 mb-5">
          展示模块依赖关系与架构分层：实线箭头 = 核心依赖，虚线 = 弱耦合。
          {entryModules.length > 0 && ` 入口模块: ${entryModules.map(m => shortName(m.path)).join('、')}。`}
          {leafModules.length > 0 && ` 叶子模块: ${leafModules.map(m => shortName(m.path)).join('、')}。`}
        </p>
        <div ref={containerRef} className="mermaid-container bg-gray-50/50 rounded-lg border border-gray-100 p-4 overflow-x-auto min-h-[500px]" />
      </div>

      {/* Info cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">🏗 架构风格</h4>
          <p className="text-sm text-gray-600 leading-relaxed">
            {report.overview.architecture_style}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="px-2.5 py-1 bg-indigo-50 text-indigo-600 text-xs font-medium rounded-lg border border-indigo-100">
              {report.overview.language}
            </span>
            <span className="px-2.5 py-1 bg-purple-50 text-purple-600 text-xs font-medium rounded-lg border border-purple-100">
              {report.overview.framework}
            </span>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">📊 关键指标</h4>
          <div className="grid grid-cols-2 gap-3">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-800">{report.metrics.total_modules}</div>
              <div className="text-xs text-gray-400">模块总数</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-800">{report.modules.reduce((s, m) => s + m.depends_on.length, 0)}</div>
              <div className="text-xs text-gray-400">依赖边总数</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-800">{report.call_chains.length}</div>
              <div className="text-xs text-gray-400">调用链</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-800">{report.risks.length}</div>
              <div className="text-xs text-gray-400">风险点</div>
            </div>
          </div>
        </div>
      </div>

      {/* Layer breakdown */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">📐 架构分层</h3>
        <div className="space-y-3">
          {entryModules.length > 0 && (
            <div className="flex items-start gap-3">
              <div className="px-2 py-1 bg-indigo-50 text-indigo-600 text-xs font-medium rounded border border-indigo-100 whitespace-nowrap mt-0.5">入口层</div>
              <div className="flex flex-wrap gap-1.5">
                {entryModules.map(m => (
                  <code key={m.path} className="px-2 py-0.5 bg-indigo-50/50 text-indigo-700 rounded text-xs font-mono border border-indigo-100">{shortName(m.path)}</code>
                ))}
              </div>
            </div>
          )}
          {report.modules.filter(m => m.stability === 'high' && !entryModules.includes(m)).length > 0 && (
            <div className="flex items-start gap-3">
              <div className="px-2 py-1 bg-emerald-50 text-emerald-600 text-xs font-medium rounded border border-emerald-100 whitespace-nowrap mt-0.5">核心层</div>
              <div className="flex flex-wrap gap-1.5">
                {report.modules.filter(m => m.stability === 'high' && !entryModules.includes(m)).map(m => (
                  <code key={m.path} className="px-2 py-0.5 bg-emerald-50/50 text-emerald-700 rounded text-xs font-mono border border-emerald-100">{shortName(m.path)}</code>
                ))}
              </div>
            </div>
          )}
          {report.modules.filter(m => m.stability === 'medium').length > 0 && (
            <div className="flex items-start gap-3">
              <div className="px-2 py-1 bg-amber-50 text-amber-600 text-xs font-medium rounded border border-amber-100 whitespace-nowrap mt-0.5">业务层</div>
              <div className="flex flex-wrap gap-1.5">
                {report.modules.filter(m => m.stability === 'medium').map(m => (
                  <code key={m.path} className="px-2 py-0.5 bg-amber-50/50 text-amber-700 rounded text-xs font-mono border border-amber-100">{shortName(m.path)}</code>
                ))}
              </div>
            </div>
          )}
          {report.modules.filter(m => m.stability === 'low' || m.stability === 'volatile').length > 0 && (
            <div className="flex items-start gap-3">
              <div className="px-2 py-1 bg-red-50 text-red-500 text-xs font-medium rounded border border-red-100 whitespace-nowrap mt-0.5">波动层</div>
              <div className="flex flex-wrap gap-1.5">
                {report.modules.filter(m => m.stability === 'low' || m.stability === 'volatile').map(m => (
                  <code key={m.path} className="px-2 py-0.5 bg-red-50/50 text-red-500 rounded text-xs font-mono border border-red-100">{shortName(m.path)}</code>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Reading guide */}
      {report.overview.reading_guide && report.overview.reading_guide.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">📖 代码导航路径</h3>
          <div className="relative">
            <div className="absolute left-3 top-2 bottom-2 w-0.5 bg-indigo-100" />
            <div className="space-y-4">
              {report.overview.reading_guide.map((step, i) => (
                <div key={i} className="flex items-start gap-4 relative">
                  <div className="w-6 h-6 rounded-full bg-indigo-500 text-white flex items-center justify-center text-xs font-bold flex-shrink-0 z-10 shadow-sm">
                    {i + 1}
                  </div>
                  <div className="bg-gray-50 rounded-lg px-4 py-3 border border-gray-100 flex-1">
                    <p className="text-sm text-gray-700">{step}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// Build Mermaid architecture diagram from report data
// ═══════════════════════════════════════════════════════════════

function buildArchitectureDiagram(report: ArchitectureReport): string {
  const lines: string[] = [];
  lines.push('graph LR');
  lines.push('');

  const safeId = (s: string): string => {
    return 'M' + s.replace(/[^a-zA-Z0-9]/g, '_').slice(0, 36);
  };

  // ── Layer-based subgraphs ─────────────────────────────────
  const entryModules = report.modules.filter(m => m.depended_by.length >= 2 && m.depends_on.length <= 1);
  const coreModules = report.modules.filter(m => m.stability === 'high' && !entryModules.includes(m));
  const bizModules = report.modules.filter(m => m.stability === 'medium');
  const lowModules = report.modules.filter(m => m.stability === 'low' || m.stability === 'volatile');

  // Subgraph: core layer
  if (coreModules.length > 0) {
    lines.push('  subgraph core["🔵 核心层 — 高稳定性基础组件"]');
    coreModules.forEach(m => {
      const desc = m.responsibility.length > 0
        ? m.responsibility.replace(/"/g, "'").slice(0, 40)
        : shortName(m.path);
      lines.push(`    ${safeId(m.path)}["${shortName(m.path)}<br/><small>${desc}</small>"]`);
    });
    lines.push('  end');
    lines.push('');
  }

  // Subgraph: entry layer
  if (entryModules.length > 0) {
    lines.push('  subgraph entry["🟣 入口层 — 被多处依赖的门面"]');
    entryModules.forEach(m => {
      const desc = m.responsibility.replace(/"/g, "'").slice(0, 40);
      lines.push(`    ${safeId(m.path)}["${shortName(m.path)}<br/><small>${desc}</small>"]`);
    });
    lines.push('  end');
    lines.push('');
  }

  // Subgraph: business layer
  if (bizModules.length > 0) {
    lines.push('  subgraph biz["🟡 业务层 — 中等稳定性的功能模块"]');
    bizModules.forEach(m => {
      lines.push(`    ${safeId(m.path)}["${shortName(m.path)}"]`);
    });
    lines.push('  end');
    lines.push('');
  }

  // Subgraph: volatile layer
  if (lowModules.length > 0) {
    lines.push('  subgraph vol["🔴 波动层 — 频繁变更 / 不稳定"]');
    lowModules.forEach(m => {
      lines.push(`    ${safeId(m.path)}["${shortName(m.path)}"]`);
    });
    lines.push('  end');
    lines.push('');
  }

  // ── Edges: show actual dependencies ───────────────────────
  // Build edge list sorted by importance (cross-layer edges first, then by PageRank weight)
  interface EdgeInfo { from: string; to: string; fromStable: string; toStable: string; weight: number; }
  const allEdges: EdgeInfo[] = [];

  report.modules.forEach(m => {
    m.depends_on.forEach(dep => {
      const target = report.modules.find(t => t.path === dep);
      if (!target) return; // external dep
      allEdges.push({
        from: m.path,
        to: dep,
        fromStable: m.stability,
        toStable: target.stability,
        weight: m.depends_on.length + target.depended_by.length,
      });
    });
  });

  // Sort: cross-layer first, then by weight descending
  allEdges.sort((a, b) => {
    const aCross = a.fromStable !== a.toStable ? 0 : 1;
    const bCross = b.fromStable !== b.toStable ? 0 : 1;
    if (aCross !== bCross) return aCross - bCross;
    return b.weight - a.weight;
  });

  // Take top 35 edges for readability
  const shownEdges = allEdges.slice(0, 35);
  const seenEdgeKeys = new Set<string>();

  shownEdges.forEach(e => {
    const key = `${e.from}|${e.to}`;
    if (seenEdgeKeys.has(key)) return;
    seenEdgeKeys.add(key);

    const fid = safeId(e.from);
    const tid = safeId(e.to);

    // Edge style based on relationship type
    if (e.fromStable === 'high' && e.toStable === 'high') {
      // Core → Core: strong solid
      lines.push(`  ${fid} ==>|"核心依赖"| ${tid}`);
    } else if (e.fromStable === 'low' || e.toStable === 'low') {
      // Involving volatile: dashed
      lines.push(`  ${fid} -.->|"弱耦合"| ${tid}`);
    } else if (e.fromStable === 'high' && (e.toStable === 'medium')) {
      // Core → Business
      lines.push(`  ${fid} -->|"提供服务"| ${tid}`);
    } else {
      lines.push(`  ${fid} --> ${tid}`);
    }
  });

  // ── If no edges, still show connections from call chains ───
  if (shownEdges.length === 0 && report.call_chains.length > 0) {
    lines.push('');
    lines.push('  %% 基于调用链推断的数据流');
    report.call_chains.slice(0, 3).forEach((chain, ci) => {
      for (let i = 0; i < chain.sequence.length - 1; i++) {
        const a = safeId(chain.sequence[i]);
        const b = safeId(chain.sequence[i + 1]);
        lines.push(`  ${a} -.->|"调用链${ci + 1}"| ${b}`);
      }
    });
  }

  // ── Style classes ─────────────────────────────────────────
  lines.push('');
  lines.push('  classDef entryClass fill:#e0e7ff,stroke:#6366f1,stroke-width:2px,color:#3730a3');
  lines.push('  classDef coreClass fill:#d1fae5,stroke:#10b981,stroke-width:2px,color:#065f46');
  lines.push('  classDef bizClass fill:#fef3c7,stroke:#f59e0b,stroke-width:1.5px,color:#92400e');
  lines.push('  classDef volClass fill:#fee2e2,stroke:#ef4444,stroke-width:1.5px,color:#991b1b');

  entryModules.forEach(m => lines.push(`  class ${safeId(m.path)} entryClass`));
  coreModules.forEach(m => lines.push(`  class ${safeId(m.path)} coreClass`));
  bizModules.forEach(m => lines.push(`  class ${safeId(m.path)} bizClass`));
  lowModules.forEach(m => lines.push(`  class ${safeId(m.path)} volClass`));

  return lines.join('\n');
}

async function renderMermaid(container: HTMLDivElement, diagram: string) {
  container.innerHTML = '';
  const id = `mermaid-arch-${Date.now()}`;
  try {
    const { svg } = await mermaid.render(id, diagram);
    container.innerHTML = svg;
  } catch (err) {
    console.error('Mermaid render failed:', err, 'Diagram:', diagram.slice(0, 500));
    container.innerHTML = `<div class="text-center py-16 text-gray-400">
      <p class="font-medium text-red-500">架构图渲染失败</p>
      <p class="text-xs mt-1 mb-2">${(err as Error).message || '未知错误'}</p>
      <details class="text-left mt-2"><summary class="text-xs cursor-pointer">查看源码</summary>
        <pre class="text-xs mt-2 max-h-40 overflow-auto">${escapeHtml(diagram)}</pre>
      </details>
    </div>`;
  }
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
