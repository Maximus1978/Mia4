# ADR-0007: UI & API Contract (Phase 2 MVP)

Status: Draft  
Date: 2025-08-26  
Authors: MIA4 Team

## Context

Phase 2 introduces a minimal UI shell with streaming token generation. Need consistent, testable API without hardcoded model/preset lists in frontend. Existing event system emits Generation* events. Need admin vs user surfaces.

## Decision

Provide FastAPI-based HTTP layer exposing:

- GET /health -> {status:"ok"}
- GET /config -> {ui_mode:"admin"|"user"}
- GET /models -> dynamic model list from registry (future commit)
- POST /generate -> SSE (text/event-stream) stream of generation events

SSE event types (name -> data JSON):

- token: {seq,int, text,str, tokens_out,int, request_id, model_id}
- usage: {request_id, model_id, prompt_tokens,int, output_tokens,int, latency_ms,int, decode_tps,float}
- error: {request_id, model_id, code,error_type, message}
- end: {request_id, status:"ok"|"error"}

Reasoning preset application logged via ReasoningPresetApplied event; not a separate SSE frame (frontend can ignore). Frontend sends overrides.reasoning_preset and server merges preset values.

Session model: in-memory store {session_id -> deque[Message]}; Message {role, content, ts}. Limit: 50 messages; TTL 60m idle. No persistence.

Feature flag ui_mode controlled by ENV MIA_UI_MODE (non-config operational flag); not persisted in config registry. Admin mode unlocks additional panels; safe toggle showAdvanced (local only) can further hide optional panels.

Metrics additions (names tentative):

- api_request_total{route,method,status}
- api_request_errors_total{route,code}
- sse_stream_open_total / sse_stream_close_total{reason}
- generation_first_token_latency_ms histogram
- generation_decode_tps histogram
- session_messages_total{role}
- reasoning_preset_applied_total{mode}

No new public YAML config keys in this ADR. All limits (TTL, max messages) are internal constants.

## Alternatives Considered

1. WebSocket instead of SSE: more bi-directional but unnecessary for read-only token stream; SSE simpler and sufficient.
2. Embedding admin/user logic purely client-side: insecure; server-sent ui_mode required to avoid accidental exposure.
3. Persisting sessions to disk: defers data governance decisions; MVP keeps ephemeral.

## Consequences

- Simple streaming path; leverages existing events.
- Minimal surface; easy to test.
- No backpressure beyond HTTP flow-control.
- Admin mode still restart-bound (must relaunch to change ui_mode).

## Future Work

- /feedback endpoint (persist rating)
- /sessions/{id}/history (if needed for multi-tab sync)
- WebSocket multiplexing for advanced telemetry
- Persisted memory / RAG integration

## Status Tracking

Implementation will proceed in ordered steps (health/config -> models -> generate streaming -> presets -> metrics -> frontend integration).
