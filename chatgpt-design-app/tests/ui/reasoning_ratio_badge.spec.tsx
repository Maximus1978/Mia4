import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import PerfPanel from '../../src/components/Chat/PerfPanel';
import type { UsageEvent } from '../../src/api';

const usageWithRatio = (ratio: number): UsageEvent => ({
  request_id: 'req',
  model_id: 'model',
  prompt_tokens: 10,
  output_tokens: 20,
  latency_ms: 100,
  decode_tps: 10,
  reasoning_tokens: Math.round(ratio * 100),
  final_tokens: 100,
  reasoning_ratio: ratio,
});

describe('Reasoning ratio badge', () => {
  it('shows ALERT badge when ratio exceeds threshold', () => {
    const usage = usageWithRatio(0.5);
    render(
      <PerfPanel
        usage={usage}
        wasCancelled={false}
        ratioThreshold={0.35}
        e2eMs={null}
        contextLength={null}
      />
    );
    expect(screen.getByText('ALERT')).toBeInTheDocument();
    expect(screen.getByText(/reasoning:/)).toHaveClass('reasoning-ratio over');
  });

  it('omits ALERT badge when ratio below threshold', () => {
    const usage = usageWithRatio(0.2);
    render(
      <PerfPanel
        usage={usage}
        wasCancelled={false}
        ratioThreshold={0.35}
        e2eMs={null}
        contextLength={null}
      />
    );
    expect(screen.queryByText('ALERT')).toBeNull();
  });
});

