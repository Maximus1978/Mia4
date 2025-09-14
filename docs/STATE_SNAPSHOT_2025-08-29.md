# STATE SNAPSHOT – 2025-08-29

## 1. Summary
Stage 1 reasoning/final separation implemented: marker mode (baseline) + optional Harmony tag mode (buffered). Marker: `===FINAL===`; Harmony tags: `<analysis>`, `<final>`.

## 2. Implemented
- Postproc pipeline (`core/llm/postproc.py`) refactored.
- Harmony tag parsing (buffered) with fallback to marker.
- Suppression of reasoning_text in marker mode when `drop_from_history=true`.
- Tests: marker split, fallback, truncate, ngram suppression, reasoning suppression; harmony split + fallback.
- Config keys: llm.prompt.harmony.* documented & active.
- ADR-0014 updated (Accepted; Harmony Stage 1 section).

## 3. Deferred / Not Implemented
- Incremental (streaming) Harmony parsing (Stage 2).
- SSE channel `analysis` (separate event stream).
- Metric `harmony_tag_mismatch_total`.
- Consistent application of `drop_from_history` to Harmony (policy pending).
- Removal of marker directive after Harmony reliability validation.

## 4. Open Risks
- Buffering in Harmony increases latency for very long outputs (bounded by typical answers; monitor).
- Potential model non-compliance with tags → fallback hides issue unless monitored (need mismatch metric).

## 5. Next Sprint Seeds
- Implement incremental Harmony streaming & `analysis` SSE channel.
- Add mismatch metric + alerting.
- Integrate reasoning_ratio alert for Harmony path.
- Consider adaptive max_output_tokens heuristic.

## 6. Quick Start (Harmony)
Enable in config or env:
```
llm:
  prompt:
    harmony:
      enabled: true
```
Model must be prompted (system prompt layering) to output tags. If absent → automatic fallback.

## 7. Test Matrix
| Feature | Test File |
|---------|-----------|
| Marker split | tests/core/test_postproc_reasoning_split.py |
| N-gram suppression | tests/core/test_postproc_reasoning_split.py::test_ngram_suppression |
| Reasoning suppression (marker) | tests/core/test_postproc_reasoning_split.py::test_reasoning_not_in_history_store_semantics |
| Harmony split | tests/core/test_postproc_harmony.py::test_harmony_split_basic |
| Harmony fallback | tests/core/test_postproc_harmony.py::test_harmony_fallback_no_tags |

## 8. Decision Links
- ADR-0014 (updated for Harmony Stage 1)

## 9. Usage Notes
Client SHOULD NOT persist reasoning_text even if present (Harmony Stage 1) – treat as ephemeral debug surface.

## 10. Metrics
Currently emitted: reasoning_tokens, final_tokens, reasoning_ratio, reasoning_buffer_latency_ms. Planned: harmony_tag_mismatch_total, reasoning_ratio_alert_total (Harmony).
