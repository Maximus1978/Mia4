# UI Contract: Reasoning None Label

## Purpose

Verify that when a generation completes with zero reasoning tokens the UI shows `(none)` instead of a waiting placeholder, and does not display fused prefixes inside final answer.

## Preconditions

1. DEV mode enabled (`?dev=1` or localStorage `mia.dev=1`).
2. Backend emits `ReasoningSuppressedOrNone` event (implicit when no reasoning tokens) but UI relies only on absence of reasoning stream.

## Steps

1. Start generation with a short prompt that produces immediate final (mock or low reasoning preset).
2. Observe reasoning block header:
   - Appears only after final if dev mode is on.
   - Text: `reasoning (none)` (collapsed by default).
   - No `(waiting...)` placeholder ever displayed.
3. Expand block (optional): body remains empty (no `<pre>` section or empty `<pre>` not rendered).
4. Final assistant bubble text begins directly with model content (no leading `assistantfinal`).

## Assertions

- Header contains substring `reasoning` and `(none)` when zero reasoning tokens.
- No substring `assistantfinal` at start (case-insensitive) of final message.
- No `<|channel|>` or `<|start|>` markers present in final message DOM text.
- Collapsing/expanding reasoning header does not introduce placeholder text.

## Metrics / Telemetry (informational)

- Metric `reasoning_none_total{reason=...}` increments backend side (not asserted in UI test, covered by API/core tests).

## Regression Guard

If any of the fused markers or placeholders reappear, treat as P0 regression blocking release.
