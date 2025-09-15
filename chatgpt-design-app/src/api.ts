// Backend API integration for MIA4 Phase 2
export interface ModelInfo {
  id: string;
  role: string;
  capabilities: string[];
  context_length: number;
  flags?: { experimental?: boolean; deprecated?: boolean; alias?: boolean; reusable?: boolean; internal?: boolean };
  // Optional backend-provided limits to guide UI controls
  limits?: { max_output_tokens?: number; context_length?: number; reasoning_max_tokens?: number };
}
export interface UsageEvent { request_id: string; model_id: string; prompt_tokens: number; output_tokens: number; latency_ms: number; decode_tps: number; context_used_tokens?: number; context_total_tokens?: number; context_used_pct?: number; reasoning_tokens?: number; final_tokens?: number; reasoning_ratio?: number; }
export interface TokenEvent { seq: number; text: string; tokens_out: number; request_id: string; model_id: string; }
export interface ReasoningEvent { request_id: string; model_id: string; reasoning: string; }

// Resolve backend base URL with fallbacks:
// 1. VITE_MIA_API_URL env (vite) / localStorage override 'mia.api'
// 2. If running on :3000 assume backend :8000 same host
// 3. Otherwise same origin
function resolveBaseUrl(): string {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const envUrl = (import.meta as any)?.env?.VITE_MIA_API_URL as string | undefined;
  const ls = typeof localStorage !== 'undefined' ? localStorage.getItem('mia.api') || undefined : undefined;
  if (envUrl) return envUrl.replace(/\/$/, '');
  if (ls) return ls.replace(/\/$/, '');
  if (typeof window !== 'undefined') {
    const { protocol, hostname, port } = window.location;
    if (port === '3000') return `${protocol}//${hostname}:8000`;
    return `${protocol}//${hostname}${port ? ':' + port : ''}`;
  }
  return 'http://127.0.0.1:8000';
}

const BASE_URL = resolveBaseUrl();

export async function fetchConfig() {
  const r = await fetch(`${BASE_URL}/config`);
  if (!r.ok) throw new Error('config-failed');
  return r.json();
}

export async function fetchModels(): Promise<ModelInfo[]> {
  let r: Response;
  try {
    r = await fetch(`${BASE_URL}/models`);
  } catch (e) {
    // try secondary heuristic if first attempt fails (common mismatch: backend on 8015 during dev)
    if (BASE_URL.endsWith(':8000')) {
      try {
        const alt = BASE_URL.replace(':8000', ':8015');
        // eslint-disable-next-line no-console
        console.warn('[api] primary models fetch failed, trying', alt);
        r = await fetch(`${alt}/models`);
      } catch (e2) {
        throw new Error('models-connect-failed');
      }
    } else {
      throw new Error('models-connect-failed');
    }
  }
  if (!r.ok) throw new Error('models-failed');
  const data = await r.json();
  return data.models;
}

export async function fetchPresets(): Promise<Record<string, Record<string, number>>> {
  const r = await fetch(`${BASE_URL}/presets`);
  if (!r.ok) throw new Error('presets-failed');
  const data = await r.json();
  return (data?.reasoning_presets ?? {}) as Record<string, Record<string, number>>;
}

export interface StreamCallbacks {
  onToken?: (ev: TokenEvent) => void;
  onUsage?: (ev: UsageEvent) => void;
  onReasoning?: (ev: ReasoningEvent) => void;
  onError?: (err: { code: string; message: string }) => void; // code = error_type
  onEnd?: (status: string) => void;
}

export interface StreamHandle {
  cancel: () => void;
  getRequestId: () => string | null;
}

export async function postAbort(request_id: string): Promise<void> {
  try {
    await fetch(`${BASE_URL}/generate/abort`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ request_id })
    });
  } catch { /* best-effort */ }
}

export function streamGenerate(params: { session_id: string; model: string; prompt: string; overrides?: any }, cb: StreamCallbacks): StreamHandle {
  const es = new EventSource(`${BASE_URL}/generate`, { withCredentials: false });
  // Fallback: we can't send POST body via native EventSource. For MVP we switch to fetch + ReadableStream.
  es.close();
  const controller = new AbortController();
  let reqId: string | null = null;
  (async () => {
    const resp = await fetch(`${BASE_URL}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
      signal: controller.signal,
    });
    if (!resp.ok || !resp.body) {
      cb.onError?.({ code: 'http', message: `status ${resp.status}` });
      cb.onEnd?.('error');
      return;
    }
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buffer.indexOf('\n\n')) !== -1) {
        const frame = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        if (!frame.trim()) continue;
        const lines = frame.split('\n');
        let event: string | undefined;
        const dataLines: string[] = [];
        for (const line of lines) {
          if (line.startsWith('event:')) event = line.slice(6).trim();
          else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
        }
        const jsonStr = dataLines.join('\n');
        try {
          const obj = JSON.parse(jsonStr);
          // Capture request_id as early as possible (meta/token/usage/etc)
          if (!reqId && (obj.request_id || obj.requestId)) {
            reqId = (obj.request_id || obj.requestId) as string;
          }
          switch (event) {
            case 'token': cb.onToken?.(obj as TokenEvent); break;
            case 'reasoning': {
              // Normalize to ReasoningEvent interface
              const reasoning = (obj.reasoning ?? obj.reasoning_text ?? '') as string;
              cb.onReasoning?.({ request_id: obj.request_id, model_id: obj.model_id, reasoning });
              break;
            }
            case 'usage': cb.onUsage?.(obj as UsageEvent); break;
            case 'error': cb.onError?.({ code: obj.code || obj.error_type || 'error', message: obj.message }); break;
            case 'end': cb.onEnd?.(obj.status); break;
          }
        } catch (e) {
          cb.onError?.({ code: 'parse', message: (e as Error).message });
        }
      }
    }
    cb.onEnd?.('ok');
  })();
  return {
    cancel: () => { if (reqId) void postAbort(reqId); controller.abort(); },
    getRequestId: () => reqId,
  };
}
