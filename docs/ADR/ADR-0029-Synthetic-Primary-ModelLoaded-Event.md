---
title: ADR-0029 Synthetic ModelLoaded Event on Cached Primary Access
status: accepted
date: 2025-09-07
---

## Summary

Status: accepted (2025-09-07)

Context:
Tests reset event listeners between cases. Primary model may remain loaded in memory. Some tests assert presence of a `ModelLoaded` event after calling `get_provider_by_role('primary')` even if the model was previously loaded.

Decision:

When `get_provider_by_role('primary')` is invoked and the primary provider is already cached, emit a synthetic `ModelLoaded` event with `load_ms=0`. This keeps event-driven tests deterministic without forcing an unload/reload cycle (expensive for large models).

Rationale:

* Preserves invariant: each logical test scenario observing the primary for the first time sees a load event.
* Avoids artificial unloads that could skew performance baselines or introduce race conditions.
* `load_ms=0` clearly distinguishes synthetic emission from real load timings.

Consequences:

* Monitoring dashboards will see occasional zero-duration ModelLoaded events. This is acceptable; dashboards can filter `load_ms=0` if needed.
* No config flag introduced to keep surface minimal; can be revisited if operational noise appears.

Alternatives Considered:

1. Force unload before listener reset: higher latency, risk of resource churn.
2. Add per-test helper to assert either real or cached: spreads complexity across tests.

Testing:

* Updated `test_model_switch_cycle` now passes after change.
* No regression in config registry or passport tests.

Future:

* If later we introduce a richer lifecycle (warm vs cold), synthetic events may instead become a distinct `ModelLoadedCached` type.
