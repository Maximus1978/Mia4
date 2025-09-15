import React, { useState, useEffect } from 'react';
import SessionsList from './SessionsList';
import Diary from './Diary';
import ProjectFolders from './ProjectFolders';
import SettingsIcon from './SettingsIcon';
import ModelSelector from './ModelSelector';
import SettingsPopover, { GenerationSettings } from '../Settings/SettingsPopover';
import { fetchModels, fetchPresets, ModelInfo } from '../../api';

interface Props { model: string | null; onModelChange: (m: string) => void; settings: GenerationSettings; onSettingsChange: (s: GenerationSettings) => void }

const LeftPanel: React.FC<Props> = ({ model, onModelChange, settings, onSettingsChange }: Props) => {
    const [isOpen, setIsOpen] = useState(true);
    const [showSettings, setShowSettings] = useState(false);
    const [limits, setLimits] = useState<{ max_output_tokens?: number; context_length?: number; reasoning_max_tokens?: number } | undefined>(undefined);
    const [presets, setPresets] = useState<Record<string, { temperature?: number; top_p?: number; reasoning_max_tokens?: number }> | undefined>(undefined);
    const defaultSettings: GenerationSettings = {
        reasoningPreset: 'medium',
        temperature: 0.7,
        top_p: 0.92,
        max_output_tokens: 1024,
        persona: ''
    };
    useEffect(() => { try { localStorage.setItem('mia.gen.settings', JSON.stringify(settings)); } catch {} }, [settings]);

    // Load model limits for the currently selected model to guide UI controls
    useEffect(() => {
        let cancelled = false;
        async function loadLimits() {
            try {
                const models: ModelInfo[] = await fetchModels();
                if (cancelled) return;
                const cur = (model || localStorage.getItem('mia.chat.model')) || '';
                const info = models.find(m => m.id === cur);
                setLimits(info?.limits);
            } catch {
                if (!cancelled) setLimits(undefined);
            }
        }
        loadLimits();
        const id = setInterval(loadLimits, 7000);
        return () => { cancelled = true; clearInterval(id); };
    }, [model]);

    // Load reasoning presets for UI alignment
    useEffect(() => {
        let cancelled = false;
        async function loadPresets() {
            try {
                const data = await fetchPresets();
                if (!cancelled) setPresets(data);
            } catch {
                if (!cancelled) setPresets(undefined);
            }
        }
        loadPresets();
        const id = setInterval(loadPresets, 15000);
        return () => { cancelled = true; clearInterval(id); };
    }, []);

    const togglePanel = () => {
        setIsOpen(!isOpen);
    };

    return (
        <div className={`left-panel ${isOpen ? 'open' : 'closed'}`}>
            <button onClick={togglePanel} className="toggle-button">
                {isOpen ? 'Collapse' : 'Expand'}
            </button>
            {isOpen && (
                <div className="panel-content">
                    {/* NOTE: Model/perf params (timeout, fake, max_output_tokens, temps) are single-source in configs/base.yaml (llm.*). UI will later expose safe controls & reset-to-default using those persisted defaults. */}
                    <SessionsList />
                    <Diary />
                    <ProjectFolders />
                    <SettingsIcon onClick={() => setShowSettings(true)} />
                    <ModelSelector current={model} onSelect={onModelChange} />
                                        <div className="preset-indicators">
                                                <small style={{ display:'block', opacity:0.7 }}>Preset: {settings.reasoningPreset}</small>
                                                {settings.temperature <= 0.15 && settings.top_p <= 0.85 && (
                                                    <small style={{ color:'#2d6a4f' }}>deterministic</small>
                                                )}
                                        </div>
                    <SettingsPopover
                        open={showSettings}
                        onClose={() => setShowSettings(false)}
                        defaults={defaultSettings}
                        value={settings}
                        onChange={onSettingsChange}
                        limits={limits}
                        presets={presets}
                    />
                </div>
            )}
        </div>
    );
};

export default LeftPanel;
