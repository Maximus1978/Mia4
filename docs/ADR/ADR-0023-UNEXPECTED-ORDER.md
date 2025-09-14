# ADR-0023: Handling Unexpected Harmony Channel Order

## Status

Accepted (2025-09-03)

## Context

Harmony streaming guarantees a sequence of assistant channel messages where multiple `analysis` / `commentary` messages may precede exactly one `final` message. Real model outputs or transport fragmentation can still surface anomalies:

- Repeated `final` channel
- Additional `analysis` or `commentary` after `final`
- Interleaving that suggests the model streamed further reasoning post-final

These cases must be observable for QA, perf correlation and safety heuristics without crashing or polluting user-visible output.

## Decision

Implement lightweight anomaly counters instead of hard failures:

- Metric: `harmony_unexpected_order_total{type}` with `type ∈ {extra_final,analysis_after_final,commentary_after_final,interleaved_final}`.
- Parser suppresses all post-final content (no deltas/analysis emitted) while still counting anomalies.
- No event schema change (avoids contract churn). If richer auditing needed later we will introduce a `GenerationAnomalyDetected` event via a separate ADR.

## Rationale

- Keeps streaming tolerant to imperfect providers.
- Metrics only → zero user‑visible side effects, supports dashboards & alerting.
- Fast to compute (constant time substring checks) and already integrated with existing metrics infra.

## Alternatives Considered

1. Hard Error / Abort: rejected (would degrade UX for benign noise).
2. Store anomaly segments: rejected (retention policy not defined yet; privacy risk).
3. Emit dedicated events now: deferred to keep surface minimal until tool calling lands.

## Implications

- Dashboards can alert on sudden spikes signalling provider regression.
- Future retention logic (ADR for privacy) may sample anomalous sessions for deeper inspection.

## Observability

Each increment path already covered in unit tests to be added (`test_unexpected_order_metrics`). Fail-open philosophy: metric increment best-effort; parsing continues.

## Future Work

- Optional structured anomaly event if incident triage requires payload.
- Correlate anomaly spikes with model passport versions.

## References

- Harmony Spec (OpenAI Cookbook)
- Metrics module `core/metrics.py` helper `inc_unexpected_order`
