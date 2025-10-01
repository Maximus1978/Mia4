import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import PerfPanel, { PerfPanelProps } from '../../src/components/Chat/PerfPanel';

function renderPanel(partial: Partial<PerfPanelProps>) {
  const props: PerfPanelProps = {
    usage: null,
    wasCancelled: false,
    ratioThreshold: 0.4,
    e2eMs: null,
    contextLength: null,
    ...partial,
  };
  return render(<PerfPanel {...props} />);
}

describe('PerfPanel badges & metrics contract', () => {
  it('shows CANCELLED badge when wasCancelled true without usage', () => {
    renderPanel({ wasCancelled: true });
    expect(screen.getByTestId('cancel-badge').textContent).toContain('CANCELLED');
  });

  it('does not render panel when no usage and not cancelled', () => {
    const { queryByTestId } = renderPanel({});
    expect(queryByTestId('perf-panel')).toBeNull();
  });

  it('shows CAP badge only when cap_applied true and effective_max_tokens present', () => {
    // Without cap_applied
    const usage1: any = { request_id: 'r', model_id: 'm', prompt_tokens: 10, output_tokens: 5, latency_ms: 1, decode_tps: 10, effective_max_tokens: 100, cap_applied: false };
    renderPanel({ usage: usage1 });
    expect(screen.queryByTestId('cap-badge')).toBeNull();
    // With cap_applied
    const usage2: any = { ...usage1, cap_applied: true };
    const { rerender } = renderPanel({ usage: usage2 });
    rerender(<PerfPanel usage={usage2} wasCancelled={false} ratioThreshold={0.4} e2eMs={null} contextLength={null} />);
    expect(screen.getByTestId('cap-badge').textContent).toBe('CAP');
  });

  it('shows reasoning ratio alert badge at or above threshold', () => {
    const base = { request_id: 'r', model_id: 'm', prompt_tokens: 10, output_tokens: 20, latency_ms: 1, decode_tps: 10 };
    // Below threshold
    const usageBelow: any = { ...base, reasoning_ratio: 0.39, reasoning_tokens: 39, final_tokens: 100 };
    renderPanel({ usage: usageBelow, ratioThreshold: 0.4 });
    expect(screen.queryByTestId('ratio-alert-badge')).toBeNull();
    // At threshold
    const usageAt: any = { ...base, reasoning_ratio: 0.4, reasoning_tokens: 40, final_tokens: 100 };
    const { rerender } = renderPanel({ usage: usageAt, ratioThreshold: 0.4 });
    rerender(<PerfPanel usage={usageAt} wasCancelled={false} ratioThreshold={0.4} e2eMs={null} contextLength={null} />);
    expect(screen.getByTestId('ratio-alert-badge').textContent).toBe('ALERT');
  });

  it('renders first token latency when provided', () => {
    const usage: any = { request_id: 'r', model_id: 'm', prompt_tokens: 1, output_tokens: 1, latency_ms: 5, decode_tps: 10, first_token_latency_ms: 123 };
    renderPanel({ usage });
    const el = screen.getByTestId('first-token-latency');
    expect(el.textContent).toMatch(/first_token: 123 ms/);
  });
});
