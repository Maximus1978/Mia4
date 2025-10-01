# UI Contract Spec: Tool Trace Stub (Placeholder)

## Purpose

Ensure that when a generation completes with developer mode enabled and **no tool calls occurred**, the UI renders a visible stub element stating `No tool calls`.

## Preconditions

- Dev mode enabled (`localStorage.mia.dev = '1'`).
- SSE stream for a request finishes (`event: end`).
- No `commentary` events with parsable JSON containing a `tool` field were received.
- No internal ToolCallPlanned/ToolCallResult events (future explicit SSE) were surfaced.

## Acceptance Criteria

1. After stream completion, the `ToolTracePanel` is present (`data-testid="tool-trace-panel"`).
2. Element with `data-testid="tool-trace-empty"` exists and text equals exactly `No tool calls`.
3. No list items with class `.tool-trace-entry` are rendered.
4. While streaming (before completion) and still no tool events, a `data-testid="tool-trace-pending"` placeholder MAY be shown (non-blocking). It must disappear once completed.

## Negative Cases

- If at least one tool commentary JSON with `tool` key arrives, stub MUST NOT render; instead entries list displays.
- If dev mode disabled, neither stub nor panel is rendered.

## Metrics / Observability (Future)

- (Planned) Increment `tool_trace_empty_total` when stub renders.

## Test Hooks

- Use a mock SSE driver returning only token + final events.
- Assert DOM after completion.

## Out of Scope

- Detailed tool call rendering (covered by separate spec).
