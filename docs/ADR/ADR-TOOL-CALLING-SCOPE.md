# ADR-TOOL-CALLING-SCOPE: Tool Calling MVP Scope

Status: Accepted

Date: 2025-09-04

Authors: MIA4 Team

## Context

We are introducing structured tool calling to the generation pipeline. Harmony parsing already reserves headers (`recipient:` / `to:` and `<|constrain|>` stub). We need a minimal, observable, testable slice without executing real external tools yet.

Goals:

- Define event contract for planned and completed tool calls.
- Provide metrics for frequency + latency + success/error split.
- Keep execution a no-op (return canned success) to avoid side‑effects.
- Preserve privacy / retention rules groundwork.

Non-goals (future ADRs):

- Parallel tool chains.
- Tool result caching.
- Sandboxed execution / security policy.
- Adaptive retry / backoff.

## Decision

Introduce two events:

1. `ToolCallPlanned`  
   Fields: `request_id`, `tool`, `args_preview_hash`, `seq` (order within request), optional `args_schema_version`.
2. `ToolCallResult`  
   Fields: `request_id`, `tool`, `status` (ok|error), `latency_ms`, `seq`, optional `error_type`, `message`.

Metrics:

- `tool_calls_total{tool,status}` counter increments on result.
- `tool_call_latency_ms{tool}` histogram observe on result (only if status=ok or error has latency measurement).

Parser Stub:

- Detect pseudo-markers in model output of form: `<|start|>assistant<|channel|>tool<|message|>{"tool":"NAME","arguments":{...}}<|end|>`
- Emit `ToolCallPlanned` immediately when chunk parsed.
- Immediately emit `ToolCallResult` (status=ok, latency_ms≈0) returning canned JSON: `{"ok":true}` inserted into stream as commentary channel payload with type `tool_result` (internal) converted to `commentary` outwardly.
- Limit: max tool payload size 8KB (otherwise emit error result with `error_type=tool_payload_too_large`).

Retention / Privacy:

- Hash tool arguments preview using SHA256 of the JSON canonical string truncated to first 200 chars before hash (prevents leaking huge content while still deduplicating identical calls). Stored only as `args_preview_hash`.
- No raw arguments stored in events.

Error Modes:

- Oversized payload → status=error, error_type=tool_payload_too_large.
- Malformed JSON → status=error, error_type=tool_payload_parse_error.

## Alternatives Considered

- Delaying ToolCallResult until separate execution phase: rejected for MVP (adds complexity & async management before we need it).
- Emitting raw arguments: rejected (privacy & retention concerns).

## Consequences

- Downstream components can start observing tool usage frequency & latency distribution.
- Easy future extension: replace no-op executor with dispatcher issuing real tool functions when configured.

## Testing Strategy

Unit tests:

- Parse & emit planned + result (ok path) metrics & events snapshot.
- Oversize payload triggers error path metrics.
- Malformed JSON triggers parse error path metrics.
- Event sequence ordering: Planned precedes Result; no duplicates.

Contract test: Ensure counters `tool_calls_total{tool=...,status=...}` and histogram key `tool_call_latency_ms{tool=...}` appear.

## Open Items / Follow-ups

- Tool registry & discovery manifest (deferred).
- Security policy ADR (sandbox / allowlist).
- Retention enrichment (tool chain summarization) once real execution added.

## Status Tracking

Implements SSOT task: "Tool calling stub (recipient/to + constrain no-op)" and extends with deterministic synthetic tool execution events.

Implementation Notes (2025-09-04):

- Channel `<|channel|>tool` parsed by Harmony adapter.
- Events `ToolCallPlanned` / `ToolCallResult` emitted.
- Metrics `tool_calls_total{tool,status}` and `tool_call_latency_ms{tool}` live.
- System prompt banner not yet updated to list `tool` (intentional: keep internal until retention policy ADR clarifies exposure). Future change requires updating `_build_harmony_prompt`.
