import type { ArchitectureReport, JobStatus, QAResponse } from './types';

const API_BASE = '/api';

export async function startAnalysis(repoUrl: string): Promise<{ job_id: string }> {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repo_url: repoUrl }),
  });
  if (!res.ok) throw new Error(`启动失败: ${res.statusText}`);
  return res.json();
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}`);
  if (!res.ok) throw new Error(`任务未找到: ${res.statusText}`);
  return res.json();
}

export function subscribeToJob(jobId: string, onEvent: (status: JobStatus) => void): () => void {
  const url = `${API_BASE}/jobs/${jobId}/sse`;
  const eventSource = new EventSource(url);

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data) as JobStatus;
      onEvent(data);
    } catch { /* keepalive */ }
  };

  eventSource.onerror = () => {
    if (eventSource.readyState === EventSource.CLOSED) {
      eventSource.close();
      let pollCount = 0;
      const poll = setInterval(async () => {
        try {
          const status = await getJobStatus(jobId);
          onEvent(status);
          if (['done', 'failed'].includes(status.phase)) clearInterval(poll);
          if (++pollCount > 120) clearInterval(poll);
        } catch {
          if (++pollCount > 120) clearInterval(poll);
        }
      }, 1000);
    }
  };

  return () => eventSource.close();
}

export async function getReport(jobId: string): Promise<ArchitectureReport> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}/report`);
  if (!res.ok) throw new Error(`报告未找到: ${res.statusText}`);
  return res.json();
}

/** Stream QA via SSE. Calls onToken for each token, resolves with full text on done. */
export function askQuestionStream(
  jobId: string,
  question: string,
  onToken: (token: string) => void,
  onError: (err: string) => void,
): Promise<string> {
  return new Promise((resolve) => {
    let full = '';
    fetch(`${API_BASE}/qa/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: jobId, question }),
    }).then(async (res) => {
      if (!res.ok) {
        onError(`请求失败: ${res.status}`);
        resolve(full);
        return;
      }
      const reader = res.body?.getReader();
      if (!reader) { resolve(full); return; }

      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.token) {
                full += data.token;
                onToken(data.token);
              }
              if (data.done) {
                resolve(data.full_answer || full);
                return;
              }
              if (data.error) {
                onError(data.error);
                resolve(full);
                return;
              }
            } catch { /* skip malformed */ }
          }
        }
      }
      resolve(full);
    }).catch((err) => {
      onError(err.message);
      resolve(full);
    });
  });
}

export async function askQuestion(jobId: string, question: string): Promise<QAResponse> {
  const res = await fetch(`${API_BASE}/qa`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_id: jobId, question }),
  });
  if (!res.ok) throw new Error(`问答失败: ${res.statusText}`);
  return res.json();
}
