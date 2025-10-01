import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import PerfPanel from '../../src/components/Chat/PerfPanel';
import type { UsageEvent } from '../../src/api';

const baseUsage: UsageEvent = {
  request_id: 'req-1',
  model_id: 'model-1',
  prompt_tokens: 120,
  output_tokens: 60,
  latency_ms: 250,
  decode_tps: 12.5,
};

describe('PerfPanel UI contracts', () => {
  it('renders CAP badge and progress when cap applied', () => {
    const usage = {
      ...baseUsage,
      cap_applied: true,
      effective_max_tokens: 80,
    } as UsageEvent;
    const { getByText, getByTestId } = render(
      <PerfPanel
        usage={usage}
        wasCancelled={false}
        ratioThreshold={0.35}
        e2eMs={null}
        contextLength={null}
      />
    );
    expect(getByText('CAP')).toBeInTheDocument();
    expect(getByTestId('cap-progress-fill')).toHaveStyle({ width: '75%' });
    expect(getByText('60/80 (75%)')).toBeInTheDocument();
  });

  it('renders CANCELLED badge when wasCancelled is true', () => {
    render(
      <PerfPanel
        usage={null}
        wasCancelled
        ratioThreshold={0.35}
        e2eMs={null}
        contextLength={null}
      />
    );
    expect(screen.getByText('CANCELLED')).toBeInTheDocument();
  });

  it('shows first token latency when provided', () => {
    const usage = {
      ...baseUsage,
      first_token_latency_ms: 42,
    } as UsageEvent;
    render(
      <PerfPanel
        usage={usage}
        wasCancelled={false}
        ratioThreshold={0.35}
        e2eMs={null}
        contextLength={null}
      />
    );
    expect(screen.getByText(/first_token: 42 ms/)).toBeInTheDocument();
  });

  it('omits first token latency when field absent', () => {
    render(
      <PerfPanel
        usage={baseUsage}
        wasCancelled={false}
        ratioThreshold={0.35}
        e2eMs={null}
        contextLength={null}
      />
    );
    expect(screen.queryByText(/first_token:/)).toBeNull();
  });
});

