# Changelog Phase 2 Progress (2025-08-26)

## Added

- FastAPI backend with /health, /config, /models, /generate (SSE).
- SessionStore (TTL 60m, max 50 msgs) + metrics session_messages_total.
- SSE streaming adapter mapping Generation* events to token/usage/end.
- ReasoningPresetApplied event integration and reasoning_mode metric.
- Metrics middleware (api_request_total, api_request_latency_ms, api_request_errors_total).
- Generation metrics: first token latency, latency_ms, decode_tps, sse_stream_open/close.
- Admin/User launch scripts (UI mode feature flag).
- ADR-0007 UI & API Contract.
- Frontend scaffold (chat UI shell) – initial integration pending finalize.

## Changed

- Added prompt_tokens in SSE usage frame.
- Accumulated full assistant response into session history.

## Tests

- Added API tests (health, models, stream first token, model switch, reasoning preset, decode_tps, error case).

## Documentation

- API.md created (endpoints + SSE contract).
- Updated .instructions.md Phase 2 checkboxes.

## Next

- Frontend wiring to live SSE.
- Perf validation (3 consecutive runs) before Phase 3.
