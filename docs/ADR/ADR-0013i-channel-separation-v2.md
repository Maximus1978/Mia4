# ADR-0013i: Harmony Channel Separation v2

## Status
Accepted (Draft pending merge) – September 17, 2025

## Context / Problem
Early Harmony adapter mixed channel outputs by relying on a single aggregated fragment list. This risked leaking reasoning (analysis) content into user-facing final text and provided no explicit leak/anomaly metrics. Invariants (INV-CH-ISO, INV-LEAK-METRICS) required:
- No reasoning tokens in final_text
- Metrics emitted on any channel ordering anomaly or leak condition

Observed gaps:
- Analysis tokens could appear if provider or upstream mixing occurred
- No reasoning_leak_total / channel_merge_anomaly_total metrics
- Post-final channel emissions only partially tracked (unexpected order metric existed but no leak classification)

## Decision
Implement Channel Separation v2 inside `HarmonyChannelAdapter`:
1. Maintain independent per-channel buffers: `_analysis_acc`, `_final_token_texts`, `_commentary_acc`.
2. Emit only analysis tokens as `type=analysis` events; never append them to final buffer.
3. Guard final token emission; disallowed tokens trigger `reasoning_leak_total{reason=guard_block_final_token}`.
4. On any post-final analysis segment: increment `harmony_unexpected_order_total{type=analysis_after_final}` AND `reasoning_leak_total{reason=post_final_analysis}` plus `channel_merge_anomaly_total{type=post_finalize_emission}`.
5. Finalization guard checks assembled final text for stray analysis/service markers; if found, record `reasoning_leak_total{reason=analysis_in_final}` and `channel_merge_anomaly_total{type=analysis_token_emitted_as_delta}` then sanitize.
6. Provide helper wrappers in `core.metrics` for leak/anomaly metric names to prevent naming drift.
7. Add contract & isolation tests: no analysis markers in delta tokens, metrics fire on anomalies, final frame clean of service markers.

## Alternatives Considered
- Pure streaming router split (discarding adapter parsing). Rejected: adds complexity duplicating tokenization logic; adapter already central point.
- Post-hoc sanitization only. Rejected: hides systemic leaks instead of surfacing metrics; violates observability-first principle.

## Consequences
Positive:
- Deterministic channel isolation & explicit leak observability.
- Simpler UI: can trust `delta` events to be user-visible content.
- Metrics allow alerting & regression detection.

Negative / Trade-offs:
- Slight overhead (additional string scans & metrics inc calls); negligible vs token streaming cost.
- Additional test surface; mitigated by concise targeted tests.

## Metrics Introduced
- `reasoning_leak_total{reason}` reasons: `guard_block_final_token`, `post_final_analysis`, `analysis_in_final` (extensible: `service_marker_in_final`, `mixed_channel_fragment`).
- `channel_merge_anomaly_total{type}` types: `post_finalize_emission`, `analysis_token_emitted_as_delta` (future: `commentary_token_in_final`).

## Test Matrix
| Scenario | Expected | Metrics |
|----------|----------|---------|
| Normal analysis then final | No analysis in delta | none of the leak/anomaly counters increment |
| Post-final analysis | No new deltas; analysis events suppressed | `harmony_unexpected_order_total{type=analysis_after_final}`, `reasoning_leak_total{reason=post_final_analysis}`, `channel_merge_anomaly_total{type=post_finalize_emission}` |
| Final frame guard with injected analysis marker (simulated) | Sanitized final output | `reasoning_leak_total{reason=analysis_in_final}` + anomaly |
| Guard-blocked token (future n-gram disallow) | Token suppressed | `reasoning_leak_total{reason=guard_block_final_token}` |

## Implemented Files
- `core/llm/adapters.py` – channel buffers, leak instrumentation, final guard.
- `core/metrics.py` – helper wrappers & metric name documentation.
- Tests:
  - `tests/core/test_channel_isolation.py`
  - `tests/core/test_history_guard.py`
  - `tests/core/test_sse_channel_separation.py`

## Invariants Mapping
- INV-CH-ISO → Enforced by separation & final guard.
- INV-LEAK-METRICS → Emission on each leak/anomaly path.

## Open Follow-Ups
- UI: reasoning block collapse (P1) now can rely on clean separation.
- Potential additional anomaly reasons (commentary in final) after broader provider validation.
- Add perf micro-benchmark to ensure overhead <1% token throughput (deferred).

## Decision Drivers
- Prevent silent regressions (observability-first).
- Keep logic localized (single adapter rather than multiple middleware layers).
- Maintain minimal public contract change (no API schemas altered).

## Status Criteria for Completion
- All new tests green.
- Metrics present in snapshot only under anomaly scenarios.
- ADR merged & `.instructions.md` updated referencing ADR-0013i for tasks 1c/1d/1e & 9b/9c.

## References
- Execution Plan items: 1c,1d,1e,9b,9c,13i
- Invariants: INV-CH-ISO, INV-LEAK-METRICS
