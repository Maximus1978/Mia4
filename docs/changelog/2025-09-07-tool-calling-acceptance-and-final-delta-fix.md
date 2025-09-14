# 2025-09-07 – Tool Calling MVP Acceptance & Harmony Final Delta Consistency Fix

## Summary

Accepted Tool Calling MVP (ADR-TOOL-CALLING-SCOPE) fully integrated: parser emits `tool_channel_raw`, route synthesizes `ToolCallPlanned` and `ToolCallResult` events with metrics (`tool_calls_total{tool,status}`, `tool_call_latency_ms{tool}`). Added conditional retention rules for tool chains and baseline commentary retention modes. Fixed Harmony adapter `final_tokens` inconsistency: now guarantees all counted final tokens are emitted as `delta` events (late flush on `finalize()` if consumer skipped iteration), ensuring `stats.final_tokens == visible_delta_count`.

## Details

- Added tracking `_delivered_final_tokens`; wrapper iterator increments on each emitted delta.
- `finalize()` flushes any undispatched deltas before emitting final stats.
- Events registry regenerated: includes `ToolCallPlanned`, `ToolCallResult`.
- Commentary retention baseline modes (metrics_only / hashed_slice / redacted_snippets / raw_ephemeral) covered by tests; persistent storage policy deferred.
- Conditional tool chain retention: tool call args/results retention controlled (override + metric instrumentation).

## Metrics / Observability

- Guarantees `final_tokens` represents user-visible token count (prevents drift when downstream ignores streaming deltas).
- Tool call metrics live and covered by contract test.

## Tests Added / Updated

- Extended adapter tests now pass (partial header/orphan scenario) after fix.
- Tool call events & metrics test verifying counter + histogram presence.

## Backward Compatibility

- No change to external API schema; only ensures stat correctness.
- No new config keys introduced.

## Follow-ups

- Add negative tool call tests (oversize payload, malformed JSON) with error metrics.
- System prompt banner update to explicitly mention `tool` channel or document omission.
- ADR for commentary persistent storage policy.

## Risk

Low: pure additive tracking + final flush guarded; does not alter token ordering semantics, only ensures completeness.
