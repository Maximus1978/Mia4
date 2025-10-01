import React, { useState, useRef, useEffect } from 'react';
import UserMessage from './UserMessage';
import AIMessage from './AIMessage';
import FeedbackButtons from './FeedbackButtons';
import InputBar from './InputBar';
import '../../styles/globals.css';
import PerfPanel from './PerfPanel';
import ToolTracePanel, { ToolTraceEntry } from './ToolTracePanel';
import { streamGenerate, TokenEvent, UsageEvent, ReasoningEvent, StreamHandle, fetchModels, ModelInfo, fetchConfig, CommentaryEvent } from '../../api';
import { GenerationSettings } from '../Settings/SettingsPopover';

interface Msg { type: 'user' | 'ai'; content: string }

interface ChatWindowProps { model: string | null; settings: GenerationSettings }

const ChatWindow: React.FC<ChatWindowProps> = ({ model, settings }: ChatWindowProps) => {
    const [messages, setMessages] = useState<Msg[]>(() => {
        const raw = localStorage.getItem('mia.chat.messages');
        return raw ? JSON.parse(raw) : [];
    });
    const [streaming, setStreaming] = useState<boolean>(false);
    const [lastUsage, setLastUsage] = useState<UsageEvent | null>(null);
    const [error, setError] = useState<{ code: string; message: string } | null>(null);
    const [toolTrace, setToolTrace] = useState<ToolTraceEntry[]>([]);
    const [toolTraceComplete, setToolTraceComplete] = useState<boolean>(false);
    const [latestReasoning, setLatestReasoning] = useState<string | null>(null);
    const [showReasoning, setShowReasoning] = useState<boolean>(false);
    const [devEnabled, setDevEnabled] = useState<boolean>(() => {
        try { return localStorage.getItem('mia.dev') === '1'; } catch { return false; }
    });
    const [passportWarn, setPassportWarn] = useState<{ field: string; passport: number; config: number } | null>(null);
    const [gpuWarn, setGpuWarn] = useState<{ requested?: unknown; effective?: unknown } | null>(null);
    const [e2eMs, setE2eMs] = useState<number | null>(null);
    const [wasCancelled, setWasCancelled] = useState<boolean>(false);
    const startTsRef = useRef<number | null>(null);
    const [contextLen, setContextLen] = useState<number | null>(null);
    const [ratioThreshold, setRatioThreshold] = useState<number>(() => {
        try {
            const raw = localStorage.getItem('mia.reasoning_ratio.threshold');
            if (raw) return Math.min(0.95, Math.max(0.05, parseFloat(raw)));
        } catch { /* ignore */ }
        return 0.35;
    });

    const ensureSessionId = (): string => {
        const saved = localStorage.getItem('mia.chat.session_id');
        if (saved) return saved;
        const sid = typeof crypto !== 'undefined' && (crypto as any).randomUUID ? (crypto as any).randomUUID() : Math.random().toString(36).slice(2);
        localStorage.setItem('mia.chat.session_id', sid);
        return sid;
    };
    const sessionIdRef = useRef<string>(ensureSessionId());
    const abortRef = useRef<StreamHandle | null>(null);

    const describeGpuValue = (value: unknown): string => {
        if (value === null || value === undefined) return 'auto';
        if (typeof value === 'number') {
            if (value === -1) return 'auto';
            if (value === 0) return 'cpu';
            return value.toString();
        }
        if (typeof value === 'string') {
            const trimmed = value.trim();
            if (!trimmed) return 'auto';
            const lowered = trimmed.toLowerCase();
            if (lowered === 'auto') return 'auto';
            if (trimmed === '0' || lowered === 'cpu') return 'cpu';
            return trimmed;
        }
        return String(value);
    };

    useEffect(() => {
        localStorage.setItem('mia.chat.messages', JSON.stringify(messages));
    }, [messages]);

    useEffect(() => {
        if (model) localStorage.setItem('mia.chat.model', model);
    }, [model]);

    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const cfg = await fetchConfig();
                const raw = (cfg as any)?.reasoning_ratio_threshold ?? cfg?.reasoning_ratio_threshold;
                if (!cancelled && typeof raw === 'number' && !Number.isNaN(raw)) {
                    const clamped = Math.min(0.95, Math.max(0.05, raw));
                    setRatioThreshold(clamped);
                    try { localStorage.setItem('mia.reasoning_ratio.threshold', clamped.toString()); } catch { /* ignore */ }
                }
            } catch { /* ignore */ }
        })();
        return () => { cancelled = true; };
    }, []);

    useEffect(() => {
        try {
            if (typeof window !== 'undefined') {
                const p = new URLSearchParams(window.location.search);
                if (p.get('dev') === '1') {
                    localStorage.setItem('mia.dev', '1');
                    setDevEnabled(true);
                }
            }
        } catch { /* ignore */ }
    }, []);

    useEffect(() => {
        const handleDevChange = () => {
            try {
                const newVal = localStorage.getItem('mia.dev') === '1';
                setDevEnabled(newVal);
            } catch { /* ignore */ }
        };
        window.addEventListener('mia-dev-change', handleDevChange);
        return () => window.removeEventListener('mia-dev-change', handleDevChange);
    }, []);

    useEffect(() => {
        let cancelled = false;
        async function loadCtx() {
            try {
                const models: ModelInfo[] = await fetchModels();
                if (cancelled) return;
                const info = model ? models.find(m => m.id === model) : undefined;
                setContextLen(info?.context_length ?? null);
            } catch {
                if (!cancelled) setContextLen(null);
            }
        }
        loadCtx();
        return () => { cancelled = true; };
    }, [model]);

    const handleSendMessage = (text: string) => {
        if (!text.trim()) return;
        if (!model) {
            setError({ code: 'no-model', message: 'no-model-selected' });
            return;
        }
        setWasCancelled(false);
        setError(null);
        setLastUsage(null);
    setLatestReasoning(null);
    setShowReasoning(false); // will only open automatically once reasoning arrives
        setToolTrace([]);
        setToolTraceComplete(false);
        setPassportWarn(null);
        setGpuWarn(null);
        setMessages((m: Msg[]) => [...m, { type: 'user', content: text }, { type: 'ai', content: '' }]);
        setStreaming(true);
        startTsRef.current = typeof performance !== 'undefined' ? performance.now() : null;
        const session_id = sessionIdRef.current;
        const overrides = {
            temperature: settings.temperature,
            top_p: settings.top_p,
            max_output_tokens: settings.max_output_tokens,
            persona: settings.persona || undefined,
            reasoning_preset: settings.reasoningPreset,
            dev_pre_stream_delay_ms: settings.dev_pre_stream_delay_ms ?? undefined,
            dev_per_token_delay_ms: settings.dev_per_token_delay_ms ?? undefined,
            n_gpu_layers: settings.n_gpu_layers,
        };
        abortRef.current = streamGenerate({ session_id, model, prompt: text, overrides }, {
            onToken: (ev: TokenEvent) => {
                // Render tokens exactly as provided; backend is SSOT for sanitation.
                const clean = ev.text;
                setMessages((msgs: Msg[]) => {
                    const copy = [...msgs];
                    const last = copy[copy.length - 1];
                    if (last && last.type === 'ai') {
                        last.content += clean;
                    }
                    return copy;
                });
            },
            onFinal: (f) => {
                // Replace last AI message with authoritative backend final text (SSOT)
                const finalText = f.text || '';
                setMessages((msgs: Msg[]) => {
                    const copy = [...msgs];
                    for (let idx = copy.length - 1; idx >= 0; idx--) {
                        if (copy[idx].type === 'ai') { copy[idx] = { ...copy[idx], content: finalText }; break; }
                    }
                    return copy;
                });
            },
            onReasoning: (r: ReasoningEvent) => {
                setLatestReasoning(prev => (prev ? prev + r.reasoning : r.reasoning));
                // Auto-expand only first time reasoning appears
                setShowReasoning(prev => (prev ? prev : true));
            },
            onCommentary: (evt: CommentaryEvent) => {
                const rawText = typeof evt.text === 'string' ? evt.text : '';
                let parsed: any = (evt as any)?.parsed ?? null;
                if (!parsed && rawText) {
                    try { parsed = JSON.parse(rawText); } catch { parsed = null; }
                }
                if (parsed && typeof parsed === 'object' && parsed !== null && typeof parsed.tool === 'string') {
                    const entry: ToolTraceEntry = {
                        tool: parsed.tool,
                        status: typeof parsed.status === 'string' ? parsed.status : 'unknown',
                        ok: Boolean(parsed.ok ?? (parsed.status ? parsed.status === 'ok' : false)),
                        message: parsed.message ?? parsed.error_type ?? null,
                        preview_hash: parsed.preview_hash ?? null,
                        args_redacted: parsed.args_redacted ?? null,
                        raw_args: parsed.raw_args ?? null,
                        error_type: parsed.error_type ?? null,
                    };
                    setToolTrace(prev => [...prev, entry]);
                }
            },
            onUsage: (u: UsageEvent) => setLastUsage(u),
            onWarning: (w: any) => {
                if (w && w.event === 'ModelPassportMismatch') {
                    setPassportWarn({ field: w.field, passport: w.passport_value, config: w.config_value });
                    setTimeout(() => setPassportWarn(null), 5000);
                } else if (w && w.event === 'GpuFallback') {
                    setGpuWarn({ requested: w.requested, effective: w.effective });
                    setTimeout(() => setGpuWarn(null), 5000);
                }
            },
            onError: (err) => {
                setStreaming(false);
                setToolTraceComplete(true);
                setError({ code: err.code, message: err.message });
                setMessages((msgs: Msg[]) => {
                    const copy = [...msgs];
                    const last = copy[copy.length - 1];
                    if (last && last.type === 'ai') last.content = `[error: ${err.message}]`;
                    else copy.push({ type: 'ai', content: `[error: ${err.message}]` });
                    return copy;
                });
            },
            onEnd: () => {
                setStreaming(false);
                setToolTraceComplete(true);
                if (startTsRef.current != null && typeof performance !== 'undefined') {
                    setE2eMs(Math.round(performance.now() - startTsRef.current));
                }
            }
        });
    };

    const handleCancel = () => {
        abortRef.current?.cancel();
        setStreaming(false);
        setWasCancelled(true);
        setToolTraceComplete(true);
    };

    return (
        <div className="chat-window">
            <div className="messages">
                {messages.map((m: Msg, i: number) => {
                    if (m.type === 'user') return <UserMessage key={i} content={m.content} />;
                    const isLastAI = i === messages.length - 1 && m.type === 'ai';
                    // In dev mode, show the reasoning header for the latest AI message only
                    // when reasoning tokens have arrived OR after streaming completes.
                    // This avoids any '(waiting...)' placeholder and shows '(none)' post-final.
                    const shouldShowReasoning = isLastAI && devEnabled && (
                        (latestReasoning != null && latestReasoning.length > 0) || !streaming
                    );
                    return (
                        <div key={i} className="ai-wrapper">
                            {shouldShowReasoning && (
                                <div className="reasoning-block">
                                    <div className="reasoning-header" onClick={() => setShowReasoning(s => !s)}>
                                        <strong>reasoning</strong>
                                        {latestReasoning ? (showReasoning ? ' ▾' : ' ▸') : (
                                            streaming ? '' : ' (none)'
                                        )}
                                        {/* No '(waiting...)' placeholder before first token */}
                                    </div>
                                    {showReasoning && latestReasoning && (
                                        <pre className="reasoning-body">{latestReasoning}</pre>
                                    )}
                                </div>
                            )}
                            <AIMessage content={m.content} />
                        </div>
                    );
                })}
            </div>
            <FeedbackButtons />
            <InputBar onSendMessage={handleSendMessage} disabled={!model || streaming} />
            {passportWarn && (
                <div className="toast warn">
                    Warning: ModelPassportMismatch on {passportWarn.field}. Passport={passportWarn.passport} vs Config={passportWarn.config}
                </div>
            )}
            {gpuWarn && (
                <div className="toast warn">
                    Warning: GPU fallback (requested {describeGpuValue(gpuWarn.requested)} → effective {describeGpuValue(gpuWarn.effective)})
                </div>
            )}
            {streaming && (
                <div className="stream-indicator">
                    Streaming...
                    <button className="cancel-btn" onClick={handleCancel}>Cancel</button>
                </div>
            )}
            {devEnabled && (
                <div className="dev-banner">
                    <span>DEV MODE</span>
                    <button onClick={() => {
                        localStorage.removeItem('mia.dev');
                        setDevEnabled(false);
                        window.dispatchEvent(new CustomEvent('mia-dev-change'));
                    }}>disable</button>
                </div>
            )}
            {(lastUsage || wasCancelled) && (
                <PerfPanel
                    usage={lastUsage}
                    wasCancelled={wasCancelled}
                    ratioThreshold={ratioThreshold}
                    e2eMs={e2eMs}
                    contextLength={contextLen}
                />
            )}
            <ToolTracePanel
                devEnabled={devEnabled}
                events={toolTrace}
                streaming={streaming}
                completed={toolTraceComplete}
            />
            {error && <div className="error-banner">Error [{error.code}]: {error.message}</div>}
        </div>
    );
};

export default ChatWindow;
