import React, { useState, useRef, useEffect } from 'react';
import UserMessage from './UserMessage';
import AIMessage from './AIMessage';
import FeedbackButtons from './FeedbackButtons';
import InputBar from './InputBar';
import '../../styles/globals.css';
import { streamGenerate, TokenEvent, UsageEvent, ReasoningEvent, StreamHandle, fetchModels, ModelInfo } from '../../api';
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
    const [latestReasoning, setLatestReasoning] = useState<string | null>(null);
    const [showReasoning, setShowReasoning] = useState<boolean>(false);
    const [e2eMs, setE2eMs] = useState<number | null>(null);
    const startTsRef = useRef<number | null>(null);
    const [contextLen, setContextLen] = useState<number | null>(null);

    useEffect(() => {
        let cancelled = false;
        async function loadCtx() {
            try {
                const models: ModelInfo[] = await fetchModels();
                if (cancelled) return;
                const info = model ? models.find(m => m.id === model) : undefined;
                setContextLen(info?.context_length ?? null);
            } catch { if (!cancelled) setContextLen(null); }
        }
        loadCtx();
        return () => { cancelled = true; };
    }, [model]);
        // Stable session id across reloads (was incorrectly storing a function leading to missing session_id in JSON -> 422)
        function _initSessionId(): string {
            const saved = localStorage.getItem('mia.chat.session_id');
            if (saved) return saved;
            const sid = typeof crypto !== 'undefined' && (crypto as any).randomUUID ? (crypto as any).randomUUID() : Math.random().toString(36).slice(2);
            localStorage.setItem('mia.chat.session_id', sid);
            return sid;
        }
        const sessionIdRef = useRef<string>(_initSessionId());
    useEffect(() => {
        localStorage.setItem('mia.chat.messages', JSON.stringify(messages));
    }, [messages]);

    useEffect(() => {
        if (model) localStorage.setItem('mia.chat.model', model);
    }, [model]);
    const abortRef = useRef<StreamHandle | null>(null);

    const handleSendMessage = (text: string) => {
        if (!text.trim()) return;
        if (!model) {
            setError({ code: 'no-model', message: 'no-model-selected' });
            return;
        }
            setMessages((m: Msg[]) => [...m, { type: 'user', content: text }, { type: 'ai', content: '' }]);
        setStreaming(true);
            startTsRef.current = performance.now();
            const session_id = sessionIdRef.current; // ensured string
        const overrides = {
            temperature: settings.temperature,
            top_p: settings.top_p,
            max_output_tokens: settings.max_output_tokens,
            persona: settings.persona || undefined,
            reasoning_preset: settings.reasoningPreset,
            dev_pre_stream_delay_ms: settings.dev_pre_stream_delay_ms ?? undefined,
            dev_per_token_delay_ms: settings.dev_per_token_delay_ms ?? undefined,
        };
        abortRef.current = streamGenerate({ session_id, model, prompt: text, overrides }, {
            onToken: (ev: TokenEvent) => {
                    setMessages((msgs: Msg[]) => {
                        const copy: Msg[] = [...msgs];
                    const last = copy[copy.length - 1];
                    if (last && last.type === 'ai') last.content += ev.text;
                    return copy;
                });
            },
            onReasoning: (r: ReasoningEvent) => {
                setLatestReasoning(r.reasoning);
                setShowReasoning(true);
            },
                onUsage: (u: UsageEvent) => setLastUsage(u),
        onError: (err) => {
                setStreaming(false);
            setError({ code: err.code, message: err.message });
                    setMessages((msgs: Msg[]) => {
                        const copy = [...msgs];
                        const last = copy[copy.length - 1];
                        if (last && last.type === 'ai') last.content = `[error: ${err.message}]`;
                        else copy.push({ type: 'ai', content: `[error: ${err.message}]` });
                        return copy;
                    });
            },
            onEnd: () => { setStreaming(false); if (startTsRef.current != null) setE2eMs(Math.round(performance.now() - startTsRef.current)); }
        });
    };
    const handleCancel = () => {
        abortRef.current?.cancel();
        setStreaming(false);
    };

    return (
            <div className="chat-window">
            <div className="messages">
                {messages.map((m: Msg, i: number) => {
                    if (m.type === 'user') return <UserMessage key={i} content={m.content} />;
                    // AI message
                    const isLastAI = i === messages.length - 1 && latestReasoning;
                    return (
                        <div key={i} className="ai-wrapper">
                            {isLastAI && latestReasoning && (
                                <div className="reasoning-block">
                                    <div className="reasoning-header" onClick={() => setShowReasoning(s => !s)}>
                                        <strong>reasoning</strong> {showReasoning ? '▼' : '▲'}
                                    </div>
                                    {showReasoning && <pre className="reasoning-body">{latestReasoning}</pre>}
                                </div>
                            )}
                            <AIMessage content={m.content} />
                        </div>
                    );
                })}
            </div>
            <FeedbackButtons />
            <InputBar onSendMessage={handleSendMessage} disabled={!model || streaming} />
            {streaming && <div className="stream-indicator">Streaming... <button className="cancel-btn" onClick={handleCancel}>Cancel</button></div>}
                {lastUsage && (
                    <div className="perf-panel">
                        <span>latency: {lastUsage.latency_ms} ms</span>{' '}
                        <span>decode_tps: {lastUsage.decode_tps.toFixed(1)}</span>{' '}
                        <span>tokens: in {lastUsage.prompt_tokens} / out {lastUsage.output_tokens}</span>
                        {(() => {
                            const used = (lastUsage.context_used_tokens != null)
                                ? lastUsage.context_used_tokens
                                : (lastUsage.prompt_tokens + lastUsage.output_tokens);
                            const total = (lastUsage.context_total_tokens != null)
                                ? lastUsage.context_total_tokens
                                : contextLen ?? null;
                            if (typeof total === 'number') {
                                const pct = Math.min(100, Math.round((used / Math.max(1, total)) * 100));
                                return <span> context: {used}/{total} ({pct}%)</span>;
                            }
                            return null;
                        })()}
                        {typeof e2eMs === 'number' && <span> e2e: {e2eMs} ms</span>}
                        {typeof lastUsage.reasoning_ratio === 'number' && (
                            <span>
                                {' '}reasoning: {lastUsage.reasoning_tokens ?? 0}/{lastUsage.final_tokens ?? lastUsage.output_tokens} ({(lastUsage.reasoning_ratio * 100).toFixed(0)}%)
                            </span>
                        )}
                    </div>
                )}
                {error && <div className="error-banner">Error [{error.code}]: {error.message}</div>}
        </div>
    );
};

export default ChatWindow;
