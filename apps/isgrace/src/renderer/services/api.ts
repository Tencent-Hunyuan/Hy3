import type { Config, Material, LLMSettings, SettingsResponse, AuthMeResponse, StreamChunk } from '../../types';
import { useStore } from '../store/useStore';

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '/api';

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { credentials: 'include' });
  if (!res.ok) throw new Error(`GET ${path} failed: HTTP_${res.status}`);
  return res.json() as Promise<T>;
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path} failed: HTTP_${res.status}`);
  return res.json() as Promise<T>;
}

/** A visitor's personal key override (hosted mode only) — never sent to /api/settings, only attached per-LLM-call. */
function localKeyOverrideBody(): { settingsOverride: LLMSettings } | Record<string, never> {
  const override = useStore.getState().localKeyOverride;
  return override?.apiKey ? { settingsOverride: override } : {};
}

// ── API ───────────────────────────────────────────────────────────────────────

export const api = {
  config: {
    load: (): Promise<Config> => getJSON('/config'),
    save: (config: Partial<Config>): Promise<Config> => postJSON('/config', config),
  },

  file: {
    uploadMaterial: async (file: File): Promise<Material> => {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(`${API_BASE}/materials`, { method: 'POST', credentials: 'include', body: formData });
      if (!res.ok) throw new Error(`Upload failed: HTTP_${res.status}`);
      return res.json() as Promise<Material>;
    },

    uploadUrl: (url: string): Promise<Material> => postJSON('/materials/from-url', { url }),

    deleteMaterial: async (id: string): Promise<void> => {
      const res = await fetch(`${API_BASE}/materials/${id}`, { method: 'DELETE', credentials: 'include' });
      if (!res.ok) throw new Error(`Delete failed: HTTP_${res.status}`);
    },
  },

  llm: {
    /** Streams a chat completion, invoking onChunk for every SSE chunk until done. */
    chat: async (
      payload: { messages: Array<{ role: string; content: string }>; reasoningEffort?: 'high' | 'low' | 'none' },
      onChunk: (chunk: StreamChunk) => void,
    ): Promise<void> => {
      const streamId = crypto.randomUUID();
      let res: Response;
      try {
        res = await fetch(`${API_BASE}/llm/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ ...payload, ...localKeyOverrideBody() }),
        });
      } catch (err) {
        onChunk({ id: streamId, delta: '', done: true, error: err instanceof Error ? err.message : 'NETWORK_ERROR' });
        return;
      }

      if (!res.ok || !res.body) {
        onChunk({ id: streamId, delta: '', done: true, error: `HTTP_${res.status}` });
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data: ')) continue;
          const data = trimmed.slice(6);
          if (!data) continue;
          try {
            onChunk(JSON.parse(data) as StreamChunk);
          } catch { /* skip malformed chunk */ }
        }
      }
    },

    /** Grade an essay or code answer via LLM. */
    grade: (payload: {
      questionId: string; type: 'essay' | 'code';
      question: string; rubric: string; answer: string; points: number;
    }): Promise<{ questionId: string; correct: boolean; score: number; maxScore: number; explanation: string }> =>
      postJSON('/llm/grade', { ...payload, ...localKeyOverrideBody() }),
  },

  settings: {
    load: (): Promise<SettingsResponse> => getJSON('/settings'),
    save: (s: Partial<LLMSettings>): Promise<LLMSettings> => postJSON('/settings', s),
    testConnection: (s: LLMSettings): Promise<{ ok: boolean; error?: string }> =>
      postJSON('/settings/test-connection', s),
  },

  auth: {
    login: (email: string): Promise<{ email: string }> => postJSON('/auth/login', { email }),
    me: (): Promise<AuthMeResponse> => getJSON('/auth/me'),
  },

  cheatsheet: {
    save: async (content: string): Promise<string> => {
      const { path } = await postJSON<{ path: string }>('/cheatsheets', { content });
      return path;
    },
  },
};
