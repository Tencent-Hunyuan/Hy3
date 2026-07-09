import { useState, useMemo } from 'react';
import type { ArchitectureReport } from '../types';
import { OverviewTab } from './tabs/OverviewTab';
import { ModulesTab } from './tabs/ModulesTab';
import { DepGraphTab } from './tabs/DepGraphTab';
import { ArchitectureDiagramTab } from './tabs/ArchitectureDiagramTab';
import { CallChainsTab } from './tabs/CallChainsTab';
import { RisksTab } from './tabs/RisksTab';
import { DeployGuideTab } from './tabs/DeployGuideTab';
import { QATab } from './tabs/QATab';

type TabId = 'overview' | 'modules' | 'depgraph' | 'archdiagram' | 'callchains' | 'risks' | 'deploy' | 'qa';

const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: 'overview', label: '概览', icon: '📋' },
  { id: 'modules', label: '模块', icon: '🧩' },
  { id: 'depgraph', label: '依赖图', icon: '🔗' },
  { id: 'archdiagram', label: '架构流程', icon: '🗺️' },
  { id: 'callchains', label: '调用链', icon: '⚡' },
  { id: 'risks', label: '风险', icon: '⚠️' },
  { id: 'deploy', label: '部署指南', icon: '🚀' },
  { id: 'qa', label: '追问', icon: '💬' },
];

interface Props {
  report: ArchitectureReport;
  jobId: string;
}

export function ReportTabs({ report, jobId }: Props) {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  // Keep tabs mounted so QA chat persists across switches
  const [mountedTabs] = useState<Set<TabId>>(() => new Set(['overview']));

  // Track which tabs have been visited so we can lazy-mount them
  useMemo(() => { mountedTabs.add(activeTab); }, [activeTab]);

  return (
    <div className="mt-2">
      {/* Tab bar */}
      <div className="flex gap-0 border-b border-gray-200 mb-8 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-3 text-sm font-medium whitespace-nowrap transition-all
              ${activeTab === tab.id
                ? 'text-indigo-600 border-b-2 border-indigo-600 bg-indigo-50/50'
                : 'text-gray-500 hover:text-gray-700 hover:border-b-2 hover:border-gray-200'
              }
            `}
          >
            <span className="mr-1.5">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="min-h-[400px]">
        <div style={{ display: activeTab === 'overview' ? 'block' : 'none' }}>
          <OverviewTab report={report} jobId={jobId} />
        </div>
        <div style={{ display: activeTab === 'modules' ? 'block' : 'none' }}>
          <ModulesTab report={report} />
        </div>
        <div style={{ display: activeTab === 'depgraph' ? 'block' : 'none' }}>
          <DepGraphTab report={report} />
        </div>
        <div style={{ display: activeTab === 'archdiagram' ? 'block' : 'none' }}>
          <ArchitectureDiagramTab report={report} />
        </div>
        <div style={{ display: activeTab === 'callchains' ? 'block' : 'none' }}>
          <CallChainsTab report={report} />
        </div>
        <div style={{ display: activeTab === 'risks' ? 'block' : 'none' }}>
          <RisksTab report={report} />
        </div>
        <div style={{ display: activeTab === 'deploy' ? 'block' : 'none' }}>
          <DeployGuideTab report={report} />
        </div>
        <div style={{ display: activeTab === 'qa' ? 'block' : 'none' }}>
          <QATab jobId={jobId} report={report} />
        </div>
      </div>
    </div>
  );
}
