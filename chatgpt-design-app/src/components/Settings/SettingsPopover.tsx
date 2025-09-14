import React, { useState, useEffect } from 'react';

export interface GenerationSettings {
  reasoningPreset: string;
  temperature: number;
  top_p: number;
  max_output_tokens: number;
  persona: string;
}

interface Props {
  open: boolean;
  onClose: () => void;
  defaults: GenerationSettings;
  value: GenerationSettings;
  onChange: (v: GenerationSettings) => void;
}

const clamp = (v: number, min: number, max: number) => Math.min(max, Math.max(min, v));

const SettingsPopover: React.FC<Props> = ({ open, onClose, defaults, value, onChange }) => {
  const [local, setLocal] = useState<GenerationSettings>(value);

  useEffect(() => {
    if (open) setLocal(value);
  }, [open, value]);

  if (!open) return null;

  const setField = <K extends keyof GenerationSettings>(k: K, v: GenerationSettings[K]) => {
    setLocal(prev => ({ ...prev, [k]: v }));
  };

  const applyPreset = (preset: string) => {
    // Placeholder mapping; should sync with backend presets
    const map: Record<string, { temperature: number; top_p: number }> = {
      low: { temperature: 0.6, top_p: 0.9 },
      medium: { temperature: 0.7, top_p: 0.92 },
      high: { temperature: 0.85, top_p: 0.95 }
    };
    const found = map[preset] || map.medium;
    setLocal(prev => ({ ...prev, reasoningPreset: preset, temperature: found.temperature, top_p: found.top_p }));
  };

  const isCustom = (() => {
    const presetVals: Record<string, { temperature: number; top_p: number }> = {
      low: { temperature: 0.6, top_p: 0.9 },
      medium: { temperature: 0.7, top_p: 0.92 },
      high: { temperature: 0.85, top_p: 0.95 }
    };
    const p = presetVals[local.reasoningPreset];
    if (!p) return true;
    return !(Math.abs(p.temperature - local.temperature) < 1e-6 && Math.abs(p.top_p - local.top_p) < 1e-6);
  })();

  const determinist = local.temperature <= 0.15 && local.top_p <= 0.85;

  return (
    <div className="settings-popover-overlay">
      <div className="settings-popover">
        <header>
          <h3>Generation Settings</h3>
        </header>
        <section>
          <h4>Base</h4>
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
          </div>
          <div className="form-row">
            <label>Top_p</label>
            <input type="range" min={0.1} max={1} step={0.01} value={local.top_p} onChange={e => setField('top_p', clamp(parseFloat(e.target.value),0.1,1))} />
            <input className="numeric" type="number" min={0.1} max={1} step={0.01} value={local.top_p} onChange={e => setField('top_p', clamp(parseFloat(e.target.value),0.1,1))} />
          </div>
          <div className="form-row">
            <label>Max tokens</label>
            <input className="numeric" type="number" min={16} max={8192} step={16} value={local.max_output_tokens} onChange={e => setField('max_output_tokens', Math.max(1, parseInt(e.target.value)||0))} />
          </div>
          <div className="form-row persona">
            <label>Persona</label>
            <textarea maxLength={1200} value={local.persona} placeholder="Persona (tone, style, role)..." onChange={e => setField('persona', e.target.value)} />
            <div className="char-counter">{local.persona.length}/1200</div>
          </div>
          <div className="form-row">
            {determinist && <span className="badge deterministic">Deterministic</span>}
          </div>
        </section>
        <section>
          <h4>Advanced (planned)</h4>
          <div className="planned-note">Repetition penalty, Top_k, Stop sequences, Presence/Frequency penalties, Persona length indicator.</div>
        </section>
        <section>
          <h4>Expert / Perf (planned)</h4>
          <div className="planned-note">Context length strategy, n_threads, n_batch, Abort generation control.</div>
        </section>
        <footer>
          <button onClick={() => setLocal(defaults)}>Default</button>
          <div className="spacer" />
            <button onClick={onClose} className="secondary">Cancel</button>
            <button onClick={() => { onChange(local); onClose(); }} className="primary">Save</button>
        </footer>
      </div>
    </div>
  );
};

export default SettingsPopover;
