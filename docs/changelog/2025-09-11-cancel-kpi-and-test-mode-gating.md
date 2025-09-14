# 2025-09-11 — Cancel KPI and Test-mode Gating

Summary:

- Completed B7 cancellation KPI: ensured `GenerationCancelled` and `CancelLatencyMeasured` are emitted across exception, late-success, and finalizer paths. Added centralized cancel latency metric emission.
- Implemented B8+B9 sampling tagging: merged_sampling now includes `mode="custom"` when user overrides are present.
- Gated test-only helpers in `/generate` route under `MIA_TEST_MODE=1`:
  - Meta SSE frame at stream start.
  - Small pre-stream delay when dev overrides are present.
  - Deferred timer backstop for late-arriving abort intent after stream end.
  Production path clears abort registry immediately with no deferred emissions.
- Updated API docs to mention test-mode aids explicitly.
- ADR-0031 documents meta SSE and late-cancel backstop behavior.

Tests:

- Cancel latency KPI integration test green.
- Full suite: 123 passed, 12 skipped in venv.

Risks:

- Ensure environment flag `MIA_TEST_MODE` is not set in production.
- Monitor `generation_cancelled_total{reason}` and `cancel_latency_events_total{path}` for unexpected spikes post-deploy.
