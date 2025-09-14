import React, { useState, useEffect } from 'react';
import SessionsList from './SessionsList';
import Diary from './Diary';
import ProjectFolders from './ProjectFolders';
import SettingsIcon from './SettingsIcon';
import ModelSelector from './ModelSelector';
import SettingsPopover, { GenerationSettings } from '../Settings/SettingsPopover';

interface Props { model: string | null; onModelChange: (m: string) => void; settings: GenerationSettings; onSettingsChange: (s: GenerationSettings) => void }

const LeftPanel: React.FC<Props> = ({ model, onModelChange, settings, onSettingsChange }: Props) => {
    const [isOpen, setIsOpen] = useState(true);
    const [showSettings, setShowSettings] = useState(false);
    const defaultSettings: GenerationSettings = {
        reasoningPreset: 'medium',
        temperature: 0.7,
        top_p: 0.92,
        max_output_tokens: 1024,
        persona: ''
    };
    useEffect(() => { try { localStorage.setItem('mia.gen.settings', JSON.stringify(settings)); } catch {} }, [settings]);

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
                    />
                </div>
            )}
        </div>
    );
};

export default LeftPanel;