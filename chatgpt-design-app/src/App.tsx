import React, { useState } from 'react';
import LeftPanel from './components/LeftPanel/LeftPanel';
import ChatWindow from './components/Chat/ChatWindow';
import './styles/globals.css';
import './styles/theme.css';
import { GenerationSettings } from './components/Settings/SettingsPopover';

const App = () => {
  const [model, setModel] = useState<string | null>(null);
  const [genSettings, setGenSettings] = useState<GenerationSettings>({ reasoningPreset:'medium', temperature:0.7, top_p:0.92, max_output_tokens:1024, persona:'' });
  return (
    <div className="app-container">
  <LeftPanel model={model} onModelChange={setModel} settings={genSettings} onSettingsChange={setGenSettings} />
  <ChatWindow model={model} settings={genSettings} />
    </div>
  );
};

export default App;