import React, { useState, useEffect } from 'react';

export interface GenerationSettings {
  reasoningPreset: string;
  temperature: number;
  top_p: number;
  max_output_tokens: number;
  persona: string;
  n_gpu_layers: number | 'auto';
  // Optional dev harness controls
  dev_pre_stream_delay_ms?: number;
  dev_per_token_delay_ms?: number;
}

interface Props {
  open: boolean;
  onClose: () => void;
  defaults: GenerationSettings;
  value: GenerationSettings;
  onChange: (v: GenerationSettings) => void;
  limits?: { max_output_tokens?: number; context_length?: number; reasoning_max_tokens?: number };
  presets?: Record<string, { temperature?: number; top_p?: number; reasoning_max_tokens?: number }>;
}

const clamp = (v: number, min: number, max: number) => Math.min(max, Math.max(min, v));

const SettingsPopover: React.FC<Props> = ({ open, onClose, defaults, value, onChange, limits, presets }) => {
  const [local, setLocal] = useState<GenerationSettings>(value);
  const [devEnabled, setDevEnabled] = useState<boolean>(() => {
    try { return typeof localStorage !== 'undefined' && localStorage.getItem('mia.dev') === '1'; } catch { return false; }
  });

  useEffect(() => {
    if (open) setLocal(value);
  }, [open, value]);

  if (!open) return null;

  const setField = <K extends keyof GenerationSettings>(k: K, v: GenerationSettings[K]) => {
    setLocal(prev => ({ ...prev, [k]: v }));
  };

  const fallbackPresets: Record<string, { temperature: number; top_p: number }> = {
    low: { temperature: 0.6, top_p: 0.9 },
    medium: { temperature: 0.7, top_p: 0.92 },
    high: { temperature: 0.85, top_p: 0.95 },
  };
  const applyPreset = (preset: string) => {
    const p = (presets?.[preset] as any) || fallbackPresets[preset] || fallbackPresets.medium;
    const t = typeof p?.temperature === 'number' ? p.temperature : fallbackPresets.medium.temperature;
    const tp = typeof p?.top_p === 'number' ? p.top_p : fallbackPresets.medium.top_p;
    setLocal(prev => ({ ...prev, reasoningPreset: preset, temperature: t, top_p: tp }));
  };

  const currentPresetVals = (() => {
    const p = presets?.[local.reasoningPreset] as any;
    if (p) return { temperature: p.temperature, top_p: p.top_p };
    return fallbackPresets[local.reasoningPreset] || fallbackPresets.medium;
  })();
  const isCustom = (() => {
    const p = currentPresetVals;
    const tOk = typeof p.temperature === 'number' ? Math.abs((p.temperature as number) - local.temperature) < 1e-6 : true;
    const tpOk = typeof p.top_p === 'number' ? Math.abs((p.top_p as number) - local.top_p) < 1e-6 : true;
    return !(tOk && tpOk);
  })();
  const overridden = {
    temperature: typeof currentPresetVals.temperature === 'number' && Math.abs((currentPresetVals.temperature as number) - local.temperature) >= 1e-6,
    top_p: typeof currentPresetVals.top_p === 'number' && Math.abs((currentPresetVals.top_p as number) - local.top_p) >= 1e-6,
  };

  const determinist = local.temperature <= 0.15 && local.top_p <= 0.85;
  const overriddenMax = typeof limits?.max_output_tokens === 'number' ? (local.max_output_tokens !== limits.max_output_tokens) : false;
  const overriddenPersona = (local.persona || '').trim().length > 0;
  const defaultGpuLayers = defaults?.n_gpu_layers ?? 'auto';
  const gpuOverridden = local.n_gpu_layers !== defaultGpuLayers;
  const gpuModeBadge = (() => {
    if (local.n_gpu_layers === 'auto') return null;
    if (local.n_gpu_layers === 0) return 'cpu';
    return `${local.n_gpu_layers}`;
  })();

  return (
    <div className="settings-popover-overlay">
      <div className="settings-popover">
        <header>
          <h3>Generation Settings</h3>
        </header>
        <section>
          <h4>Base</h4>
          <div className="form-row">
            <label>Developer mode</label>
            <input
              type="checkbox"
              checked={devEnabled}
              onChange={(e) => {
                const v = e.target.checked;
                setDevEnabled(v);
                try { 
                  if (v) localStorage.setItem('mia.dev', '1'); 
                  else localStorage.removeItem('mia.dev'); 
                  // Notify ChatWindow about dev mode change
                  window.dispatchEvent(new CustomEvent('mia-dev-change'));
                } catch {}
              }}
            />
          </div>
          <div className="form-row">
            <label>Reasoning preset</label>
            <select value={local.reasoningPreset} onChange={e => applyPreset(e.target.value)}>
              <option value="low">low</option>
              <option value="medium">medium</option>
              <option value="high">high</option>
            </select>
            {isCustom && <span className="badge">custom</span>}
          </div>
          <div className="form-row">
            <label>Temperature</label>
            <input type="range" min={0} max={2} step={0.01} value={local.temperature} onChange={e => setField('temperature', clamp(parseFloat(e.target.value),0,2))} />
            <input className="numeric" type="number" min={0} max={2} step={0.01} value={local.temperature} onChange={e => setField('temperature', clamp(parseFloat(e.target.value),0,2))} />
            {overridden.temperature && <span className="badge" style={{ marginLeft: 8 }}>overridden</span>}
          </div>
          <div className="form-row">
            <label>Top_p</label>
            <input type="range" min={0.1} max={1} step={0.01} value={local.top_p} onChange={e => setField('top_p', clamp(parseFloat(e.target.value),0.1,1))} />
            <input className="numeric" type="number" min={0.1} max={1} step={0.01} value={local.top_p} onChange={e => setField('top_p', clamp(parseFloat(e.target.value),0.1,1))} />
            {overridden.top_p && <span className="badge" style={{ marginLeft: 8 }}>overridden</span>}
          </div>
          <div className="form-row">
            <label>Max tokens</label>
            <input
              className="numeric"
              type="number"
              min={16}
              max={limits?.max_output_tokens ?? 8192}
              step={16}
              value={local.max_output_tokens}
              onChange={e => setField('max_output_tokens', Math.max(1, parseInt(e.target.value)||0))}
            />
            {limits?.max_output_tokens && (
              <small style={{ marginLeft: 8, opacity: 0.7 }}>limit: {limits.max_output_tokens}</small>
            )}
            {overriddenMax && <span className="badge" style={{ marginLeft: 8 }}>overridden</span>}
          </div>
          <div className="form-row">
            <label>GPU layers</label>
            <input
              className="numeric"
              type="number"
              min={0}
              step={1}
              placeholder="auto"
              value={local.n_gpu_layers === 'auto' ? '' : local.n_gpu_layers}
              onChange={(e) => {
                const raw = e.target.value;
                if (raw === '' || raw == null) {
                  setField('n_gpu_layers', 'auto');
                  return;
                }
                const parsed = Number.parseInt(raw, 10);
                if (Number.isNaN(parsed) || parsed < 0) {
                  setField('n_gpu_layers', 0);
                } else {
                  setField('n_gpu_layers', Math.max(0, parsed));
                }
              }}
            />
            <button type="button" onClick={() => setField('n_gpu_layers', 'auto')}>auto</button>
            <button type="button" onClick={() => setField('n_gpu_layers', 0)}>cpu</button>
            {gpuOverridden && <span className="badge" style={{ marginLeft: 8 }}>overridden</span>}
            {gpuModeBadge && <span className="badge" style={{ marginLeft: 8 }}>{gpuModeBadge}</span>}
          </div>
          <div className="gpu-note">leave blank for auto offload; set 0 to force CPU</div>
          <div className="form-row persona">
            <label>Persona</label>
            <textarea maxLength={1200} value={local.persona} placeholder="Persona (tone, style, role)..." onChange={e => setField('persona', e.target.value)} />
            <div className="char-counter">{local.persona.length}/1200</div>
            {overriddenPersona && <span className="badge" style={{ marginLeft: 8 }}>overridden</span>}
          </div>
          <div className="form-row">
            {determinist && <span className="badge deterministic">Deterministic</span>}
          </div>
        </section>
        {limits && (
          <section>
            <h4>Model Limits</h4>
            <div className="planned-note">
              context: {limits.context_length ?? 'n/a'}
              {typeof limits.reasoning_max_tokens === 'number' && (
                <>
                  {' '}| reasoning tokens: {limits.reasoning_max_tokens}
                </>
              )}
            </div>
          </section>
        )}
        {devEnabled && (
          <section>
            <h4>Dev Harness</h4>
            <div className="form-row">
              <label>Pre-stream delay (ms)</label>
              <input className="numeric" type="number" min={0} max={1000} step={10} value={local.dev_pre_stream_delay_ms ?? 0} onChange={e => setField('dev_pre_stream_delay_ms', Math.max(0, parseInt(e.target.value)||0))} />
            </div>
            <div className="form-row">
              <label>Per-token delay (ms)</label>
              <input className="numeric" type="number" min={0} max={200} step={1} value={local.dev_per_token_delay_ms ?? 0} onChange={e => setField('dev_per_token_delay_ms', Math.max(0, parseInt(e.target.value)||0))} />
            </div>
          </section>
        )}
        {devEnabled && (
          <>
            <section>
              <h4>Advanced (planned)</h4>
              <div className="planned-note">Repetition penalty, Top_k, Stop sequences, Presence/Frequency penalties, Persona length indicator.</div>
            </section>
            <section>
              <h4>Expert / Perf (planned)</h4>
              <div className="planned-note">Context length strategy, n_threads, n_batch, Abort generation control.</div>
            </section>
          </>
        )}
        <footer>
          <button onClick={() => setLocal({ ...defaults })}>Default</button>
          <div className="spacer" />
            <button onClick={onClose} className="secondary">Cancel</button>
            <button onClick={() => { onChange(local); onClose(); }} className="primary">Save</button>
        </footer>
      </div>
    </div>
  );
};

export default SettingsPopover;
