import { useEffect, useRef, useState } from 'react';
import type { ArchitectureReport } from '../../types';

function shortName(path: string): string {
  const parts = path.replace(/\\/g, '/').split('/');
  return parts[parts.length - 1] || path;
}

interface Props { report: ArchitectureReport; }

export function DepGraphTab({ report }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [highlightedNode, setHighlightedNode] = useState<string | null>(null);
  const renderId = useRef(`depgraph-${Math.random().toString(36).slice(2, 8)}`);

  useEffect(() => {
    if (!svgRef.current || report.modules.length === 0) return;
    const cleanup = renderForceGraph(svgRef.current, report.modules, renderId.current, setHighlightedNode);
    return cleanup;
  }, [report]);

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 glow">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-800">模块依赖关系图</h3>
            <p className="text-sm text-gray-400">
              拖拽节点 · 点击高亮关联 · 滚轮缩放 · 箭头表示依赖方向（A → B 表示 A 依赖 B）
            </p>
          </div>
          <div className="flex gap-5 text-xs text-gray-400">
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" /> 高稳定</span>
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block" /> 中稳定</span>
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-red-400 inline-block" /> 低稳定</span>
          </div>
        </div>
        {highlightedNode && (
          <div className="text-xs text-indigo-600 bg-indigo-50 border border-indigo-100 rounded-lg px-3 py-1.5 mb-3 inline-block">
            已选中: <span className="font-mono font-medium">{shortName(highlightedNode)}</span>
            <button className="ml-2 text-indigo-400 hover:text-indigo-600" onClick={() => setHighlightedNode(null)}>✕ 取消</button>
          </div>
        )}
        <svg ref={svgRef} className="w-full rounded-xl bg-gray-50/50 border border-gray-100" style={{ height: 600 }} />
      </div>

      {/* Module list grid */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
        <h4 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">模块清单</h4>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
          {report.modules.map((m) => (
            <div key={m.path} className="flex items-center gap-2 text-xs text-gray-500 px-2.5 py-2 rounded-lg bg-gray-50 border border-gray-100">
              <span className="w-2 h-2 rounded-full flex-shrink-0"
                style={{ background: m.stability === 'high' ? '#34d399' : m.stability === 'medium' ? '#fbbf24' : '#f87171' }} />
              <span className="truncate font-mono">{shortName(m.path)}</span>
              <span className="ml-auto text-gray-300 text-[10px]">←{m.depended_by.length} →{m.depends_on.length}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// D3 force-directed graph with proper arrows and highlight
// ═══════════════════════════════════════════════════════════════

function renderForceGraph(
  svgEl: SVGSVGElement,
  modules: ArchitectureReport['modules'],
  renderId: string,
  setHighlighted: (path: string | null) => void,
): () => void {
  svgEl.innerHTML = '';

  const W = svgEl.clientWidth || 800;
  const H = 600;

  // ── Build graph data ──────────────────────────────────────
  const nodeMap = new Map<string, number>();
  const nodes: any[] = [];

  modules.forEach((m, i) => {
    nodeMap.set(m.path, i);
    const totalDegree = m.depends_on.length + m.depended_by.length;
    nodes.push({
      id: i,
      name: shortName(m.path),
      path: m.path,
      stability: m.stability,
      inDeg: m.depended_by.length,
      outDeg: m.depends_on.length,
      radius: Math.max(8, Math.min(28, 8 + totalDegree * 0.8)),
    });
  });

  const links: any[] = [];
  modules.forEach((m) => {
    const srcIdx = nodeMap.get(m.path);
    if (srcIdx === undefined) return;
    m.depends_on.forEach((dep) => {
      const tgtIdx = nodeMap.get(dep);
      if (tgtIdx !== undefined) {
        links.push({ source: srcIdx, target: tgtIdx });
      }
    });
  });

  // ── D3 setup ──────────────────────────────────────────────
  const svg = (window as any).d3.select(svgEl);
  const g = svg.append('g');

  // Zoom behavior
  const zoom = (window as any).d3.zoom()
    .scaleExtent([0.2, 5])
    .on('zoom', (event: any) => { g.attr('transform', event.transform); });
  svg.call(zoom);
  svg.call(zoom.transform, (window as any).d3.zoomIdentity.translate(W / 2, H / 2));

  // ── Arrow markers (unique per render to avoid ID collisions) ──
  const defs = svg.append('defs');

  // Default arrow
  defs.append('marker')
    .attr('id', `${renderId}-arrow-default`)
    .attr('viewBox', '0 -6 12 12')
    .attr('refX', 0)   // tip at connection point
    .attr('refY', 0)
    .attr('markerWidth', 8)
    .attr('markerHeight', 8)
    .attr('orient', 'auto-start-reverse')
    .append('path')
    .attr('d', 'M12,-5L0,0L12,5')
    .attr('fill', '#c4b5fd')
    .attr('opacity', 0.6);

  // Highlight arrow
  defs.append('marker')
    .attr('id', `${renderId}-arrow-highlight`)
    .attr('viewBox', '0 -6 12 12')
    .attr('refX', 0)
    .attr('refY', 0)
    .attr('markerWidth', 10)
    .attr('markerHeight', 10)
    .attr('orient', 'auto-start-reverse')
    .append('path')
    .attr('d', 'M12,-6L0,0L12,6')
    .attr('fill', '#6366f1')
    .attr('opacity', 0.9);

  // ── Force simulation ──────────────────────────────────────
  const simulation = (window as any).d3.forceSimulation(nodes)
    .force('link', (window as any).d3.forceLink(links)
      .id((d: any) => d.id)
      .distance((l: any) => 80 + (nodes[l.source.id]?.radius || 8) + (nodes[l.target.id]?.radius || 8))
    )
    .force('charge', (window as any).d3.forceManyBody().strength(-350))
    .force('center', (window as any).d3.forceCenter(0, 0))
    .force('collide', (window as any).d3.forceCollide().radius((d: any) => d.radius + 8))
    .alphaDecay(0.02);

  // ── Render links ──────────────────────────────────────────
  const link = g.append('g')
    .selectAll('line')
    .data(links)
    .join('line')
    .attr('stroke', '#d4d4d8')
    .attr('stroke-width', 1.5)
    .attr('stroke-opacity', 0.6)
    .attr('marker-end', `url(#${renderId}-arrow-default)`);

  // ── Render nodes ──────────────────────────────────────────
  const node = g.append('g')
    .selectAll('g')
    .data(nodes)
    .join('g')
    .attr('cursor', 'grab');

  // Drag behavior
  const drag = (window as any).d3.drag()
    .on('start', (event: any, d: any) => {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x; d.fy = d.y;
    })
    .on('drag', (event: any, d: any) => {
      d.fx = event.x; d.fy = event.y;
    })
    .on('end', (event: any, d: any) => {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null; d.fy = null;
    });
  node.call(drag);

  // Circles
  node.append('circle')
    .attr('r', (d: any) => d.radius)
    .attr('fill', (d: any) => {
      if (d.stability === 'high') return '#34d399';
      if (d.stability === 'medium') return '#fbbf24';
      return '#f87171';
    })
    .attr('fill-opacity', 0.85)
    .attr('stroke', (d: any) => {
      if (d.stability === 'high') return '#34d399';
      if (d.stability === 'medium') return '#fbbf24';
      return '#f87171';
    })
    .attr('stroke-opacity', 0.3)
    .attr('stroke-width', 2);

  // Labels (inside or next to node depending on size)
  node.append('text')
    .text((d: any) => d.name)
    .attr('text-anchor', 'middle')
    .attr('dy', (d: any) => d.radius + 14)
    .attr('font-size', 10)
    .attr('font-family', "'JetBrains Mono', 'Fira Code', monospace")
    .attr('fill', '#71717a')
    .attr('pointer-events', 'none');

  // ── Click highlight interaction ───────────────────────────
  let highlightedId: number | null = null;

  node.on('click', (_event: any, d: any) => {
    const d3Event = _event;
    d3Event.stopPropagation();

    if (highlightedId === d.id) {
      // Deselect
      highlightedId = null;
      link
        .attr('stroke', '#d4d4d8')
        .attr('stroke-width', 1.5)
        .attr('stroke-opacity', 0.6)
        .attr('marker-end', `url(#${renderId}-arrow-default)`);
      node.select('circle').attr('fill-opacity', 0.85).attr('stroke-opacity', 0.3);
      node.select('text').attr('fill', '#71717a').attr('font-weight', 'normal');
      setHighlighted(null);
      return;
    }

    highlightedId = d.id;
    setHighlighted(d.path);

    // Find all nodes connected to d (1-hop)
    const relatedNodes = new Set<number>();
    relatedNodes.add(d.id);
    links.forEach((l: any) => {
      const s = l.source.id ?? l.source;
      const t = l.target.id ?? l.target;
      if (s === d.id) relatedNodes.add(t);
      if (t === d.id) relatedNodes.add(s);
    });

    // Dim non-related links
    link
      .attr('stroke', (l: any) => {
        const s = l.source.id ?? l.source;
        const t = l.target.id ?? l.target;
        return (s === d.id || t === d.id) ? '#818cf8' : '#e5e5ea';
      })
      .attr('stroke-width', (l: any) => {
        const s = l.source.id ?? l.source;
        const t = l.target.id ?? l.target;
        return (s === d.id || t === d.id) ? 3 : 0.5;
      })
      .attr('stroke-opacity', (l: any) => {
        const s = l.source.id ?? l.source;
        const t = l.target.id ?? l.target;
        return (s === d.id || t === d.id) ? 0.95 : 0.1;
      })
      .attr('marker-end', (l: any) => {
        const s = l.source.id ?? l.source;
        const t = l.target.id ?? l.target;
        return (s === d.id || t === d.id)
          ? `url(#${renderId}-arrow-highlight)`
          : `url(#${renderId}-arrow-default)`;
      });

    // Highlight related nodes, dim others
    node.select('circle')
      .attr('fill-opacity', (nd: any) => relatedNodes.has(nd.id) ? 0.95 : 0.08)
      .attr('stroke-opacity', (nd: any) => relatedNodes.has(nd.id) ? 0.8 : 0.05);
    node.select('text')
      .attr('fill', (nd: any) => nd.id === d.id ? '#18181b' : relatedNodes.has(nd.id) ? '#52525b' : '#e4e4e7')
      .attr('font-weight', (nd: any) => nd.id === d.id ? 'bold' : 'normal');
  });

  // Deselect on background click
  svg.on('click', () => {
    if (highlightedId !== null) {
      highlightedId = null;
      link
        .attr('stroke', '#d4d4d8').attr('stroke-width', 1.5).attr('stroke-opacity', 0.6)
        .attr('marker-end', `url(#${renderId}-arrow-default)`);
      node.select('circle').attr('fill-opacity', 0.85).attr('stroke-opacity', 0.3);
      node.select('text').attr('fill', '#71717a').attr('font-weight', 'normal');
      setHighlighted(null);
    }
  });

  // ── Tick: position links and nodes ────────────────────────
  simulation.on('tick', () => {
    link
      .attr('x1', (d: any) => d.source.x)
      .attr('y1', (d: any) => d.source.y)
      .attr('x2', (d: any) => d.target.x)
      .attr('y2', (d: any) => d.target.y);

    node.attr('transform', (d: any) => `translate(${d.x},${d.y})`);
  });

  return () => { simulation.stop(); };
}
