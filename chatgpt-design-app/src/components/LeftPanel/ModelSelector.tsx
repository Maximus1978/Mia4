import React, { useEffect, useState } from 'react';
import { fetchModels, ModelInfo } from '../../api';

interface Props { onSelect: (model: string) => void; current: string | null }

const ModelSelector: React.FC<Props> = ({ onSelect, current }: Props) => {
    const [models, setModels] = useState<ModelInfo[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let cancelled = false;
        async function load() {
            setLoading(true);
            try {
                const data = await fetchModels();
                if (cancelled) return;
                setModels(data);
                setError(null); // clear stale offline state
                // lightweight debug (dev only)
                if ((window as any).__MIA_DEBUG__) {
                    // eslint-disable-next-line no-console
                    console.log('[ModelSelector] models fetched', data.map(d => d.id));
                }
            } catch (e:any) {
                if (!cancelled) setError('offline');
            } finally { if (!cancelled) setLoading(false); }
        }
        load();
        const id = setInterval(load, 5000);
        return () => { cancelled = true; clearInterval(id); };
    }, []);

    // auto-select first model if none chosen (validate persisted exists)
    useEffect(() => {
        if (!current) {
            const persisted = localStorage.getItem('mia.chat.model');
            if (persisted && models.some(m => m.id === persisted)) {
                onSelect(persisted);
                return;
            }
        }
        if (!current && models.length > 0) onSelect(models[0].id);
    }, [models, current, onSelect]);

    return (
        <div className="model-selector">
            <label htmlFor="model-select">Model:</label>
            {loading && <span>...</span>}
            {error && models.length === 0 && <span className="error">offline</span>}
            {models.length > 0 && !loading && <span style={{ fontSize: '0.75rem', opacity: 0.6 }}>({models.length})</span>}
                            <select
                                id="model-select"
                                value={current || ''}
                                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => onSelect(e.target.value)}
                                disabled={loading || models.length === 0}
                            >
                <option value="" disabled>Select...</option>
                {models.filter(m => !m.flags?.deprecated && !m.flags?.experimental).map((m: ModelInfo) => {
                    const tags: string[] = [];
                    if (m.flags?.experimental) tags.push('exp');
                    if (m.flags?.deprecated) tags.push('dep');
                    if (m.flags?.alias) tags.push('alias');
                    return (
                        <option key={m.id} value={m.id}>
                            {m.id}{' '}{tags.length > 0 ? `(${tags.join(',')})` : ''}
                        </option>
                    );
                })}
            </select>
        </div>
    );
};

export default ModelSelector;