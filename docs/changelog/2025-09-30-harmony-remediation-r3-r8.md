# 2025-09-30 – Harmony Remediation: R3 / R6 / R8

## Summary

- Restored `ReasoningSuppressedOrNone` telemetry. `HarmonyChannelAdapter` now receives `request_id` / `model_id` via `set_context()` from `PrimaryPipeline`; `tests/core/test_reasoning_none_telemetry.py` covers event emission and `reasoning_none_total`.
- Added fused sanitation counter `fused_marker_sanitizations_total{kind}` and extended backend coverage (prefix + residue cases) in `tests/core/test_harmony_fused_sanitation.py`.
- Shipped temporary UI guard `sanitizeFinalText` with diagnostics attributes; `chatgpt-design-app/tests/ui/final_message_sanitization.spec.tsx` prevents fused-prefix leaks.
- Refreshed `.instructions.md`, ADR-0013i addendum, and Prompt handoff to reflect remediation status.

## Impacted Areas

- Backend: `core/llm/adapters.py`, `core/llm/pipeline/primary.py`, `core/metrics.py`.
- Frontend: `chatgpt-design-app/src/components/Chat/AIMessage.tsx`, `chatgpt-design-app/src/utils/sanitizeFinalText.ts`.
- Tests & Docs: `tests/core/test_reasoning_none_telemetry.py`, `tests/core/test_harmony_fused_sanitation.py`, `chatgpt-design-app/tests/ui/final_message_sanitization.spec.tsx`, `.instructions.md`, ADR-0013i addendum, `Prompt for continuation.md`.

## Validation

- `pytest tests/core/test_reasoning_none_telemetry.py -q`
- `pytest tests/core/test_harmony_fused_sanitation.py -q`
- `npm --prefix C:/MIA4/chatgpt-design-app run test -- tests/ui/final_message_sanitization.spec.tsx`

## Follow-ups

- Monitor `fused_marker_sanitizations_total{kind}` and `reasoning_none_total{reason}` dashboards; remove temporary UI guard after sustained green window.
- Next focus: Tool trace stub (INV-TOOL-TRACE) and remaining UI/API contract specs (P1).
