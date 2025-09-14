# 2025-09-03 Cap & Pipeline Consolidation

## Summary

Unified max token cap logic inside PrimaryPipeline (phase 1 extraction) and added ModelRouted + sampling observability test. Ensured legacy metrics snapshot compatibility during transition.

## Changes

- Route cap pre-processing removed; pipeline `prepare()` now authoritative for cap resolution.
- Derivation safeguard keeps `cap_applied` accurate in SSE usage/final events even if future adjustments occur.
- Added `PipelineContext.reasoning_mode` and initial `stream()` implementation.
- Emitted `ModelRouted` prior to `GenerationStarted` (ADR-0026 compliance) and added new test `test_model_routed_sampling`.
- Added legacy tuple key compatibility in `metrics.snapshot()` (ADR-0027).
- Added metrics on abort endpoint for unknown request IDs (`generation_aborted_total`).

## Metrics Impact

- `model_cap_hits_total` now increments reliably (guarded in both pipeline and route for idempotence).
- New optional counter `generation_aborted_total{reason=unknown-id}` for unmatched abort attempts (test compatibility).
- Dual key exposure in metrics snapshot (string + `(name,)`).

## Tests

- `tests/core/test_model_routed_sampling.py` validates `ModelRouted` + capped sampling fields in `GenerationStarted`.
- Updated cap / cancel tests remain green after refactor.

## Risks & Mitigations

- Temporary duplication of cap logic guarded by reset to original request before pipeline; will be removed once finalize extraction complete.
- Legacy metrics dual keys could mask missing label assertions; ADR-0027 documents removal criteria.

## Follow-ups

- Extract finalize path into pipeline and return structured `PipelineResult`.
- Add ADR for commentary retention + tool calling scope finalization.
- Implement `ModelPassportMismatch` warning event and UI cancel latency KPI.

## Traceability

- Pipeline: `core/llm/pipeline/primary.py`
- Route: `src/mia4/api/routes/generate.py`
- Metrics: `core/metrics.py`
- ADR: `docs/ADR/ADR-0027-Metrics-Snapshot-Legacy-Compatibility.md`
