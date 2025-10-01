import React from 'react';

export interface ToolTraceEntry {
  tool: string;
  status: string;
  ok: boolean;
  message?: string | null;
  preview_hash?: string | null;
  args_redacted?: string | null;
  raw_args?: string | null;
  error_type?: string | null;
}

export interface ToolTracePanelProps {
  devEnabled: boolean;
  events: ToolTraceEntry[];
  streaming: boolean;
  completed: boolean;
}

const ToolTracePanel: React.FC<ToolTracePanelProps> = ({
  devEnabled,
  events,
  streaming,
  completed,
}: ToolTracePanelProps) => {
  if (!devEnabled) {
    return null;
  }

  const hasEvents = events.length > 0;
  const showEmptyStub = completed && !streaming && !hasEvents;

  return (
    <div className="tool-trace-panel" data-testid="tool-trace-panel">
      <div className="tool-trace-header">Tool Trace</div>
      {hasEvents && (
        <ul className="tool-trace-list">
          {events.map((ev, idx) => (
            <li key={`${ev.tool}-${idx}`} className="tool-trace-entry">
              <span className="tool-trace-tool">{ev.tool}</span>
              <span className={ev.ok ? 'tool-trace-status ok' : 'tool-trace-status error'}>
                {ev.status.toUpperCase()}
              </span>
              {ev.preview_hash && (
                <span className="tool-trace-hash" title="preview hash">
                  {ev.preview_hash}
                </span>
              )}
              {ev.args_redacted && (
                <span className="tool-trace-redacted" title="arguments redacted">
                  {ev.args_redacted}
                </span>
              )}
              {ev.raw_args && (
                <span className="tool-trace-raw" title="raw arguments">
                  {ev.raw_args}
                </span>
              )}
              {ev.message && (
                <span className="tool-trace-message">{ev.message}</span>
              )}
            </li>
          ))}
        </ul>
      )}
      {showEmptyStub && (
        <div className="tool-trace-empty" data-testid="tool-trace-empty">No tool calls</div>
      )}
      {!hasEvents && !showEmptyStub && (
        <div className="tool-trace-empty" data-testid="tool-trace-pending">Waiting for tool activity...</div>
      )}
    </div>
  );
};

export default ToolTracePanel;
