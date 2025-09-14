# ADR-0024: Tool Calling MVP Scope (Superseded)

## Status

Superseded by ADR-TOOL-CALLING-SCOPE (Accepted 2025-09-04) — retained for historical intent deltas.

## Context

Harmony spec allows tool call headers (`<|start|>assistant<|recipient|>tool_name<|message|>...`). We need a minimal internal representation without committing to full execution semantics yet.

## Decision (Historical Draft)

Initial draft proposed a single `tool_call` event with raw args text and deferred metrics. Implementation diverged to a two-event model (`ToolCallPlanned` + `ToolCallResult`) with immediate synthetic execution and hashed args preview.

## Out of Scope

- Tool result streaming
- Retry / backoff strategies
- Tool permission model
- Structured arg JSON validation

## Rationale

Reduces risk: we defer execution security questions while unblocking UI surfacing of tool intent.

## Metrics (Draft vs Implemented)

- Draft: planned future `tool_call_parsed_total{recipient}` only.
- Implemented (see ADR-TOOL-CALLING-SCOPE): `tool_calls_total{tool,status}`, `tool_call_latency_ms{tool}` plus error types for oversize & parse failures.

## Alternatives Considered

Full execution now – rejected due to validation & sandbox complexity.

## Supersession Notes

Replaced by richer contract enabling observability and retention governance from day one. This file should not be used for current scope decisions.

## References

Harmony spec (tool calling section)
