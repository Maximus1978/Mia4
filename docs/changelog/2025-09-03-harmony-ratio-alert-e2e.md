# 2025-09-03 Harmony Ratio Alert E2E & Parser Stabilization

## Summary

Implemented full end-to-end reasoning ratio alert flow for Harmony streaming plus a safer incremental parser refactor.

## Changes

- Added/verified emission of `reasoning_ratio_alert_total{bucket=above|below}` during generation finalization.
- Added integration test `test_reasoning_ratio_alert_harmony_stream` covering both below and above threshold buckets (distinct token strategy to avoid n‑gram suppression side-effects).
- Refactored `HarmonyChannelAdapter.process_chunk` to support multiple sequential `<|start|>assistant` blocks (multiple analysis before final) with bounded buffer trimming.
- Fixed regression (NameError due to mis-indented `_content_start`) and restored adapter initialization.
- Ensured whitespace/service-token collapse preserved; maintained parse error metric path.
- Updated `.instructions.md`: marked ratio alert E2E tasks as completed in sections 4.1, 4.2, 10.5.

## Metrics Impact

- New counts: `reasoning_ratio_alert_total{bucket=below|...}` and `{bucket=above|...}` now validated by tests.
- No change to existing `harmony_parse_error_total` semantics.

## Tests Added / Updated

- `tests/integration/test_reasoning_ratio_alert_harmony_stream.py` (ensures two buckets increment once each for a single request).
- Existing unit metric test reaffirmed (`test_reasoning_ratio_alert_metric_buckets`).

## Implementation Notes

- Parser now slices processed segments from internal buffer after each closed message to mitigate unbounded growth.
- Final message closure triggers buffer discard to avoid post-final leakage.
- Guarded against absent Harmony tokens: fallback still emits plain final tokens (ratio=0 path unchanged).

## Risks & Mitigations

- Multi-message parsing: potential edge case with fragmented token boundaries — existing fragmented chunk tests remain green.
- N-gram guard interaction with distinct final tokens: integration test uses varied tokens to ensure token counting unaffected.

## Follow-ups

- Decide on unexpected order metric vs ADR defer.
- Implement dynamic system prompt augmentation (Knowledge cutoff, Current date, Reasoning level).
- Add `<|return|>` normalization test.
- Introduce commentary channel & tool calling scaffold.

## Traceability

- Adapter: `core/llm/adapters.py`
- Route logic (alert emission): `src/mia4/api/routes/generate.py`
- Config key: `llm.postproc.reasoning.ratio_alert_threshold` (already in `configs/base.yaml`).
- Docs updated: `.instructions.md` (operational plan & Harmony compliance checklist).

---
Prepared automatically by development assistant.
