# Changelog: 2025-09-17 Finalize Sanitation Guard

## Summary
Added defensive sanitation guard in `HarmonyChannelAdapter.finalize()` to scrub any residual Harmony service markers (`<|...|>`) that might appear in the assembled final text under rare edge cases (e.g., large `max_output_tokens` interleavings). Introduced two new reasoning leak metric reasons: `service_marker_in_final` (marker detected) and `finalize_sanitize` (sanitation applied). Debug mode (`MIA_HARMONY_DEBUG=1`) now logs before/after hash diff for traceability without dumping full text.

## Details
- Final assembly now preserves original joined final tokens for diffing.
- If service markers regex `<|[^|>]+|>` matches, we:
  - Increment `reasoning_leak_total{reason=service_marker_in_final}` and `reasoning_leak_total{reason=finalize_sanitize}`.
  - Scrub markers and recompute token counts to keep stats consistent with emitted deltas.
  - Emit debug log with chars removed and before/after short hashes.
- Existing analysis-in-final path still increments `analysis_in_final` and `analysis_token_emitted_as_delta` (merge anomaly) first; sanitation can follow if generic markers remain.

## Invariants Impact
- Strengthens INV-CH-ISO & INV-LEAK-METRICS (any sanitation path now guaranteed to emit leak metrics + scrubbed output).
- Reduces residual risk of un-scrubbed service markers surfacing in `final_text`.

## Migration / Compatibility
- No public API schema changes (only metric label cardinality extended with two additional `reason` values). Tests referencing `reasoning_leak_total` should allow new reasons (no strict enumeration yet). If enumeration becomes strict later, update test allowlist.

## Testing Plan
1. Add new unit test (TODO: `test_harmony_finalize_sanitize.py`) injecting synthetic service marker into adapter final token list before `finalize()` call to assert increments for `finalize_sanitize`.
2. Ensure existing channel separation tests remain green (already verified locally).
3. Optional: fuzz test injecting random `<|foo|>` tokens post-final to ensure adapter scrubs and counts metric.

## Risks / Mitigations
- Risk: Additional metric cardinality growth; mitigated by using only two bounded new reasons.
- Risk: Over-scrub could remove legitimate model text containing pattern `<|...|>`; considered acceptable given Harmony token namespace; future escape strategy can be implemented if needed.

## Next Steps
- Implement the unit test for sanitation path.
- Proceed with contract tests (ratio badge, CAP badge), then first_token_latency pipeline.
- Remove legacy frontend `reasoningSanitization.ts` after confirming no leaks across extended scenarios.

## Verification
- Ran subset: `test_harmony_channel_adapter.py`, `test_sse_channel_separation.py`, `test_reasoning_sanitization.py` (all passed).
