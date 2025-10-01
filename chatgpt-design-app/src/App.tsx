import React, { useEffect, useRef, useState } from 'react';
import LeftPanel from './components/LeftPanel/LeftPanel';
import ChatWindow from './components/Chat/ChatWindow';
import './styles/globals.css';
import './styles/theme.css';
import { GenerationSettings } from './components/Settings/SettingsPopover';
import { fetchConfig } from './api';

const baseDefaults: GenerationSettings = {
  reasoningPreset: 'medium',
  temperature: 0.7,
  top_p: 0.92,
  max_output_tokens: 1024,
  persona: '',
  n_gpu_layers: 'auto',
};

const normalizeGpuLayers = (value: unknown): number | 'auto' => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return Math.max(0, Math.trunc(value));
  }
  if (typeof value === 'string') {
    const trimmed = value.trim().toLowerCase();
    if (!trimmed || trimmed === 'auto') return 'auto';
    const parsed = Number.parseInt(trimmed, 10);
    if (Number.isNaN(parsed)) return 'auto';
    return Math.max(0, parsed);
  }
  return 'auto';
};

const loadStoredSettings = (base: GenerationSettings): GenerationSettings | null => {
  if (typeof window === 'undefined' || typeof localStorage === 'undefined') {
    return null;
  }
  try {
    const raw = localStorage.getItem('mia.gen.settings');
    if (!raw) return null;
    const parsed = JSON.parse(raw) ?? {};
    return {
      ...base,
      reasoningPreset: typeof parsed.reasoningPreset === 'string' ? parsed.reasoningPreset : base.reasoningPreset,
      temperature: typeof parsed.temperature === 'number' ? parsed.temperature : base.temperature,
      top_p: typeof parsed.top_p === 'number' ? parsed.top_p : base.top_p,
      max_output_tokens: typeof parsed.max_output_tokens === 'number' ? parsed.max_output_tokens : base.max_output_tokens,
      persona: typeof parsed.persona === 'string' ? parsed.persona : '',
      n_gpu_layers: normalizeGpuLayers(parsed.n_gpu_layers),
      dev_pre_stream_delay_ms: typeof parsed.dev_pre_stream_delay_ms === 'number' ? parsed.dev_pre_stream_delay_ms : undefined,
      dev_per_token_delay_ms: typeof parsed.dev_per_token_delay_ms === 'number' ? parsed.dev_per_token_delay_ms : undefined,
    };
  } catch {
    return null;
  }
};

const App: React.FC = () => {
  const hadStoredRef = useRef<boolean>(false);
  const [defaults, setDefaults] = useState<GenerationSettings>(baseDefaults);
  const [genSettings, setGenSettings] = useState<GenerationSettings>(() => {
    const stored = loadStoredSettings(baseDefaults);
    hadStoredRef.current = Boolean(stored);
    return stored ?? baseDefaults;
  });
  const [model, setModel] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const cfg = await fetchConfig();
        if (cancelled) return;
        const primary = (cfg as any)?.primary ?? {};
        const nextDefaults: GenerationSettings = {
          ...baseDefaults,
          temperature: typeof primary.temperature === 'number' ? primary.temperature : baseDefaults.temperature,
          top_p: typeof primary.top_p === 'number' ? primary.top_p : baseDefaults.top_p,
          max_output_tokens: typeof primary.max_output_tokens === 'number' ? primary.max_output_tokens : baseDefaults.max_output_tokens,
          n_gpu_layers: normalizeGpuLayers(primary.n_gpu_layers),
        };
        setDefaults(nextDefaults);
        if (!hadStoredRef.current) {
          setGenSettings((prev) => ({
            ...nextDefaults,
            persona: prev.persona ?? '',
            dev_pre_stream_delay_ms: prev.dev_pre_stream_delay_ms,
            dev_per_token_delay_ms: prev.dev_per_token_delay_ms,
          }));
        }
      } catch {
        // Config fetch is best-effort; ignore failures for UI bootstrap.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="app-container">
      <LeftPanel
        model={model}
        onModelChange={setModel}
        settings={genSettings}
        onSettingsChange={setGenSettings}
        defaults={defaults}
      />
      <ChatWindow model={model} settings={genSettings} />
    </div>
  );
};

export default App;
