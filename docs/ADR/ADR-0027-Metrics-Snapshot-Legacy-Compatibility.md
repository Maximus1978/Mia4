# ADR-0027: Metrics Snapshot Legacy Compatibility

## Status

Accepted (2025-09-03)

## Context

Earlier tests accessed `metrics.snapshot()["counters"]` assuming keys were tuples `(name, label_pairs, ...)` and used `k[0] == "metric_name"` to detect presence. The metrics module was refactored to emit flattened string keys like `name{label=value}` for readability and human diff friendliness. This broke tests that still relied on tuple indexing (e.g. cap & cancellation tests).

Changing all tests immediately would reduce velocity during the sampling/cap pipeline refactor and add churn across unrelated metric assertions that already migrated to string keys.

## Decision

Provide a transitional dual key format in `metrics.snapshot()`:

- Primary canonical key: string `metric{label=val,...}` (existing newer style)
- Legacy supplemental key: a tuple `(metric_name,)` mapping to the same counter value

This preserves backwards compatibility for tuple-index style assertions while allowing new code to prefer the string form. Only the name (without labels) is exposed in the legacy tuple to minimize duplication complexity and avoid ordering ambiguity.

## Consequences

- Memory overhead: negligible (one extra dict entry per counter)
- Potential confusion: two keys represent same underlying count; documented here and slated for removal.
- Migration path: after all tests updated to explicit string key lookups, remove legacy branch + this ADR (mark superseded) and enforce string lookup style.

## Alternatives Considered

1. Revert to tuple-only keys: would regress readability and recent improvements.
2. Immediate test rewrite: higher short-term cost and risk of missing edge tests not yet enumerated.
3. Provide helper accessor for tests: adds indirection; simplest is dual key insertion.

## Risks & Mitigations

- Risk: New tests might inadvertently rely on legacy tuple form. Mitigation: Add lint rule / grep in future sprint (`(name,)` usage) before removal.
- Risk: Label-specific assertions impossible via legacy key. Mitigation: tests needing labels already use string key path.

## Implementation Notes

Code change in `core/metrics.py` duplicates each counter: `counters[name+label_str] = v` and `counters[(name,)] = v` when absent. No change to histogram format.

## Removal Criteria

- All tests updated to use `snap.get('metric_name{label=...}')` pattern.
- No occurrences of `k[0] ==` style checks in repository.
- A follow-up ADR will deprecate and remove tuple insertion.

## Related

- ADR-0026 (Pipeline Separation) — introduced sampling refactor concurrent with this compatibility need.
- Execution Plan item 7 (Sampling & Cap Observability) relies on stable metric assertions during refactor.

## Changelog

Added in `2025-09-03` changelog entry `cap-pipeline-consolidation` (see corresponding file) referencing this ADR.
