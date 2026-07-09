import { useState, useCallback } from 'react';
import type { ArchitectureReport, JobStatus } from './types';
import { startAnalysis, subscribeToJob } from './api';
import { UrlInput } from './components/UrlInput';
import { ProgressPanel } from './components/ProgressPanel';
import { ReportTabs } from './components/ReportTabs';

type AppState = 'idle' | 'analyzing' | 'done' | 'error';

export default function App() {
  const [state, setState] = useState<AppState>('idle');
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [report, setReport] = useState<ArchitectureReport | null>(null);
  const [error, setError] = useState<string>('');

  const handleAnalyze = useCallback(async (repoUrl: string) => {
    setState('analyzing');
    setError('');
    setReport(null);
    // Show "pending" status immediately so ProgressPanel renders right away
    setJobStatus({
      job_id: '',
      phase: 'pending',
      progress_pct: 0,
      current_batch: 0,
      total_batches: 0,
      current_files: [],
      message: '正在启动分析...',
      error: '',
      estimated_remaining_sec: null,
      result: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });

    try {
      const { job_id } = await startAnalysis(repoUrl);

      const cleanup = subscribeToJob(job_id, (status) => {
        setJobStatus(status);

        if (status.phase === 'done' && status.result) {
          setReport(status.result);
          setState('done');
          cleanup();
        } else if (status.phase === 'failed') {
          setError(status.error || '分析失败');
          setState('error');
          cleanup();
        }
      });
    } catch (err: any) {
      setError(err.message || '启动分析失败');
      setState('error');
    }
  }, []);

  const handleReset = () => {
    setState('idle');
    setJobStatus(null);
    setReport(null);
    setError('');
  };

  return (
    <div className="min-h-screen bg-canvas">
      {/* Header */}
      <header className="bg-white border-b border-gray-100 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl icon-gradient flex items-center justify-center text-lg shadow-sm">
              🏛️
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900 tracking-tight">Codebase Archaeologist</h1>
              <p className="text-sm text-gray-500">Hy3 驱动的智能代码仓库理解引擎</p>
            </div>
          </div>
          {state === 'done' && (
            <button
              onClick={handleReset}
              className="px-4 py-2 text-sm bg-gray-50 hover:bg-gray-100 text-gray-600 rounded-lg transition-colors border border-gray-200"
            >
              重新分析
            </button>
          )}
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* URL Input */}
        {(state === 'idle' || state === 'error') && (
          <UrlInput onSubmit={handleAnalyze} error={error} />
        )}

        {/* Progress */}
        {state === 'analyzing' && jobStatus && (
          <ProgressPanel status={jobStatus} />
        )}

        {/* Report */}
        {state === 'done' && report && jobStatus && (
          <ReportTabs report={report} jobId={jobStatus.job_id} />
        )}
      </main>

      {/* Footer */}
      <footer className="mt-auto border-t border-gray-100 bg-white">
        <div className="max-w-7xl mx-auto px-4 py-3 text-center text-xs text-gray-400">
          Powered by Tencent Hy3 · Codebase Archaeologist v0.1.0
        </div>
      </footer>
    </div>
  );
}
