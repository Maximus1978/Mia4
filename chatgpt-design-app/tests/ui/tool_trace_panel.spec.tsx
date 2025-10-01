import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import ToolTracePanel, { ToolTraceEntry } from '../../src/components/Chat/ToolTracePanel';

describe('Tool trace panel', () => {
  const entry: ToolTraceEntry = {
    tool: 'browser.search',
    status: 'ok',
    ok: true,
    preview_hash: 'abcd1234',
    message: 'completed',
  };

  it('renders stub when dev enabled, completed, and no tool calls', () => {
    render(
      <ToolTracePanel devEnabled events={[]} streaming={false} completed />
    );
    expect(screen.getByTestId('tool-trace-empty')).toHaveTextContent('No tool calls');
  });

  it('shows tool entries when provided', () => {
    render(
      <ToolTracePanel devEnabled events={[entry]} streaming={false} completed />
    );
    expect(screen.queryByTestId('tool-trace-empty')).toBeNull();
    expect(screen.getByText('browser.search')).toBeInTheDocument();
    expect(screen.getByText('OK')).toBeInTheDocument();
  });

  it('hides panel entirely when dev disabled', () => {
    const { container } = render(
      <ToolTracePanel devEnabled={false} events={[entry]} streaming={false} completed />
    );
    expect(container).toBeEmptyDOMElement();
  });
});

