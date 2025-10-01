# Changelog 2025-09-30: Harmony Audit Gap Notes

## Summary

- Recorded newly discovered Harmony channel-separation regressions during the September 30 audit review.
- Updated `.instructions.md` remediation plan with explicit warnings for the unfixed items.

## Details

- Flagged R3 remediation gap: `core/metrics.py` still lacks the dedicated `fused_marker_sanitizations_total` counter (only generic leak labels exist). Added ⚠️ note in SSOT requiring implementation or explicit extension.
- Flagged R6 UI gap: frontend continues to render final text verbatim without the temporary fused-prefix scrub (see `chatgpt-design-app/src/components/Chat/AIMessage.tsx`). Marked as open in SSOT.
- Flagged R8 telemetry gap: `HarmonyChannelAdapter.finalize()` emits `ReasoningSuppressedOrNone` using undefined `self.request_id`/`self.model_id`, so the event and `reasoning_none_total` metric never fire. SSOT now tracks this failure until adapter is wired with request context.

## Follow-ups

- Patch Harmony adapter to receive request/model identifiers and restore `ReasoningSuppressedOrNone` emission.
- Extend metrics layer with the promised fused-marker sanitation counter (or equivalent label) and backfill tests/docs.
- Add interim frontend scrub (or alternative mitigation) for fused prefixes until server-side fix proven stable.
