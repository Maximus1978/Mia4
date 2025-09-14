# ADR-0031: SSE Meta Frame and Late-Cancel Backstop

Date: 2025-09-11
Status: Proposed (Test-mode default)

## Context

We need deterministic observation of cancel-related events and latency KPIs in integration tests. In practice, abort intents (mark_start + abort) may arrive just before or after streaming ends, leading to race conditions.

## Decision

1. Introduce an optional SSE "meta" frame at the very beginning of the /generate stream to expose request_id early to clients/tests.
2. Add a short pre-stream delay window (test-only) when dev_* overrides are provided to allow clients to wire aborts deterministically.
3. Ensure cancel observability across all paths:
   - immediate exception path (aborted/timeout)
   - late-success path before 'end'
   - finalize backstop
   - short deferred timer to catch mark_start arriving just after stream end

Meta frame and pre-stream delay are enabled only in test mode via env var `MIA_TEST_MODE=1`. The deferred timer backstop is enabled in all modes to ensure robust observability of late-arriving abort intents; it runs for a very short duration and then clears the abort registry.

## Consequences

- Tests can assert presence of GenerationCancelled and CancelLatencyMeasured consistently.
- Production streaming stays lean; no extra frames or timers.
- API documentation must mention the optional meta frame under test/dev conditions.

## Alternatives Considered

- Only exception and finalize backstops — still flaky in CI for late-arriving abort intents.
- Client-side buffering and double-stream parsing — risk of re-consumption errors.

## Follow-ups

- Update API docs to include optional meta frame (test/dev-only) and clarify ordering guarantees.
- Add configuration key (docs only; no public config yet) noting MIA_TEST_MODE behaviors.
- Remove debug prints and keep code behind env checks.
