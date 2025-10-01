import React from 'react';
import { UsageEvent } from '../../api';

type Nullable<T> = T | null | undefined;

export interface PerfPanelProps {
  usage: Nullable<UsageEvent>;
  wasCancelled: boolean;
  ratioThreshold: number;
  e2eMs: Nullable<number>;
  contextLength: Nullable<number>;
}

function formatNumber(value: Nullable<number>): string {
  if (typeof value !== 'number' || Number.isNaN(value)) return '-';
  return Math.round(value).toString();
}

function formatGpu(value: unknown): string {
  if (value === null || value === undefined) return 'auto';
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return 'auto';
    if (value === -1) return 'auto';
    if (value === 0) return 'cpu';
    return Math.trunc(value).toString();
  }
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) return 'auto';
    if (trimmed.toLowerCase() === 'auto') return 'auto';
    const parsed = Number.parseInt(trimmed, 10);
    if (Number.isNaN(parsed)) return trimmed;
    if (parsed === 0) return 'cpu';
    return parsed.toString();
  }
  return String(value);
}

const PerfPanel: React.FC<PerfPanelProps> = ({
  usage,
  wasCancelled,
  ratioThreshold,
  e2eMs,
  contextLength,
}: PerfPanelProps) => {
  if (!usage && !wasCancelled) {
    return null;
  }

  const latency = usage ? formatNumber(usage.latency_ms) : '-';
  const firstToken = usage && typeof usage.first_token_latency_ms === 'number'
    ? `${Math.trunc(usage.first_token_latency_ms)} ms`
    : null;
  const decodeTps = usage && typeof usage.decode_tps === 'number'
    ? usage.decode_tps.toFixed(1)
    : null;
  const promptTokens = usage?.prompt_tokens ?? 0;
  const outputTokens = usage?.output_tokens ?? 0;

  const capApplied = usage?.cap_applied ?? false;
  const effectiveMax = usage?.effective_max_tokens;
  const hasCapInfo = typeof effectiveMax === 'number' && effectiveMax > 0;
  const capPct = hasCapInfo
    ? Math.min(100, Math.round((outputTokens / effectiveMax) * 100))
    : null;

  const contextUsed = usage?.context_used_tokens ?? (promptTokens + outputTokens);
  const contextTotal = usage?.context_total_tokens ?? contextLength ?? null;
  const contextPct = typeof contextTotal === 'number'
    ? Math.min(100, Math.round((contextUsed / Math.max(1, contextTotal)) * 100))
    : null;

  const reasoningRatio = usage?.reasoning_ratio;
  const reasoningTokens = usage?.reasoning_tokens ?? 0;
  const finalTokens = usage?.final_tokens ?? outputTokens;
  const showReasoning = typeof reasoningRatio === 'number';
  const ratioAlert = showReasoning && reasoningRatio! >= ratioThreshold;

  const gpuEffectiveRaw = usage?.n_gpu_layers;
  const gpuRequestedRaw = usage?.requested_n_gpu_layers;
  const gpuFallback = usage?.gpu_fallback ?? false;
  const gpuOffload = usage?.gpu_offload ?? (typeof gpuEffectiveRaw === 'number' ? gpuEffectiveRaw > 0 : true);
  const hasGpuInfo =
    gpuEffectiveRaw !== undefined ||
    gpuRequestedRaw !== undefined ||
    typeof usage?.gpu_offload === 'boolean' ||
    typeof usage?.gpu_fallback === 'boolean';
  let gpuInfo: string | null = null;
  let gpuClass = 'gpu-mode';
  if (hasGpuInfo) {
    const effectiveLabel = formatGpu(gpuEffectiveRaw);
    const requestedLabel = gpuRequestedRaw !== undefined ? formatGpu(gpuRequestedRaw) : effectiveLabel;
    const baseLabel =
      gpuRequestedRaw !== undefined && requestedLabel !== effectiveLabel
        ? `${requestedLabel} → ${effectiveLabel}`
        : effectiveLabel;
    let suffix = '';
    if (gpuFallback) {
      suffix = ' (fallback)';
      gpuClass = 'gpu-mode warn';
    } else if (!gpuOffload || effectiveLabel === 'cpu') {
      suffix = ' (CPU)';
    } else if (effectiveLabel !== 'auto') {
      suffix = ' (GPU)';
    }
    gpuInfo = `gpu: ${baseLabel}${suffix}`;
  }

  return (
    <div className="perf-panel" data-testid="perf-panel">
      <span>latency: {latency} ms</span>
  {firstToken && <span data-testid="first-token-latency">first_token: {firstToken} </span>}
      {decodeTps && <span>decode_tps: {decodeTps}</span>}
      <span>tokens: in {promptTokens} / out {outputTokens}</span>
      {wasCancelled && (
        <strong className="badge cancel-badge" title="Generation cancelled" data-testid="cancel-badge">
          CANCELLED
        </strong>
      )}
      {hasCapInfo && (
        <span className="cap-progress-wrapper">
          <span
            className="cap-progress-bar"
            title={`output tokens ${outputTokens}/${effectiveMax}`}
          >
            <span
              className="cap-progress-fill"
              style={{ width: `${capPct}%` }}
              data-testid="cap-progress-fill"
            />
          </span>
          <span className="cap-progress-text">
            {outputTokens}/{effectiveMax} ({capPct}%)
          </span>
          {capApplied && (
            <strong className="badge cap-badge" title="Model output truncated by cap" data-testid="cap-badge">
              CAP
            </strong>
          )}
        </span>
      )}
      {typeof contextTotal === 'number' && (
        <span>
          {' '}context: {contextUsed}/{contextTotal} ({contextPct}%)
        </span>
      )}
      {gpuInfo && <span className={gpuClass}>{gpuInfo}</span>}
      {typeof e2eMs === 'number' && (
        <span> e2e: {Math.round(e2eMs)} ms</span>
      )}
      {showReasoning && (
        <span className={ratioAlert ? 'reasoning-ratio over' : 'reasoning-ratio'} data-testid="reasoning-ratio-block">
          {' '}reasoning: {reasoningTokens}/{finalTokens} ({(reasoningRatio! * 100).toFixed(0)}%)
          {ratioAlert && (
            <strong className="badge ratio-alert" data-testid="ratio-alert-badge">ALERT</strong>
          )}
        </span>
      )}
    </div>
  );
};

export default PerfPanel;
