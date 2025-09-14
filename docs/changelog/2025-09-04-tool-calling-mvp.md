# 2025-09-04 Tool Calling MVP

Status: Released

## Summary

Introduced Harmony `tool` channel and end-to-end Tool Calling MVP.

## Added

- Harmony parser support for `<|channel|>tool` emitting `tool_channel_raw` intermediary events.
- API route synthetic execution path: emits `ToolCallPlanned` and `ToolCallResult` events.
- Metrics: `tool_calls_total{tool,status}` counter; `tool_call_latency_ms{tool}` histogram.
- Error classifications: `tool_payload_too_large`, `tool_payload_parse_error`.
- Negative tests for oversize and malformed tool payloads.
- System prompt channel banner updated to include `tool`.

## Changed

- Final token emission deferred to `finalize()` for Harmony adapter to keep stats aligned with visible delta events.

## Invariants Preserved

- No reasoning/history leakage: analysis still excluded when `drop_from_history=true`.
- Commentary retention structure unchanged (pending ADR acceptance for detailed policy).

## Follow-ups

- Implement commentary retention modes (`metrics_only`, `hashed_slice`, etc.) per ADR-0024.
- Add interleaving post-final tool channel anomaly metric if needed.
- Optional optimization: skip re-emission of final deltas if some already streamed (adapter flag).
