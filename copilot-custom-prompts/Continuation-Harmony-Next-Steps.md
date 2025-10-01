# Continuation Prompt: Harmony Alignment & Next Steps (Fresh Chat)

## Context Snapshot (2025-09-17)
Core reference (SSOT): https://cookbook.openai.com/articles/openai-harmony

Key docs & artifacts:
- `.instructions.md` (authoritative execution plan, invariants, progress)
- `docs/ADR/ADR-0013i-channel-separation-v2.md` (channel isolation design)
- `docs/changelog/2025-09-17-ui-cap-ratio.md` (latest UI changes)
- `core/llm/adapters.py` (HarmonyChannelAdapter v2 implementation)
- `core/metrics.py` (metrics helpers: reasoning_leak_total, channel_merge_anomaly_total, model_cap_hits_total, etc.)
- `src/mia4/api/routes/generate.py` (SSE streaming route; usage & final events assembly)
- UI implementation:
  - `chatgpt-design-app/src/components/Chat/ChatWindow.tsx`
  - `chatgpt-design-app/src/styles/globals.css`
  - `chatgpt-design-app/src/api.ts`
- Tests (representative):
  - `tests/core/test_channel_isolation.py`
  - `tests/core/test_sse_channel_separation.py`
  - `tests/core/test_history_guard.py`
  - `tests/core/test_reasoning_sanitization.py` (legacy hygiene)
  - `tests/api/test_generate_cap_and_cancel.py`
- Placeholder UI test plan: `tests/ui/test_cap_badge_placeholder.md`

## Recently Completed
- Channel isolation backend (P0) + metrics + guards.
- Reasoning ratio badge (visual) & CAP progress bar + CAP badge (visual).
- UsageEvent interface extended with cap fields.
- Updated execution plan & changelog.

## Outstanding (Focus P1)
1. Contract tests:
   - Reasoning ratio badge (5c)
   - CAP badge (7f)
2. Cancelled state UX (6b) — show cancelled badge + distinct styling; spinner removal.
3. First token latency capture (11c) + SSE propagation (11d) + UI display (11e).
4. Tool trace stub: explicit "No tool calls" component (8d) + contract test (8e).
5. ADR & contract test for SSE 'warning' frame format (ModelPassportMismatch) (13j).
6. Potential reasoning leak under large max_output_tokens — add debug instrumentation env flag `MIA_HARMONY_DEBUG` + sanitation on finalize/error.
7. Config bi-directional test for reasoning ratio threshold (13k) — migrate threshold from localStorage override to config-driven key (with round-trip test & update to `Config-Registry.md`).

## Invariants to Enforce Next
- INV-RATIO-VIS (needs contract test)
- INV-CAP-UX (needs contract test)
- INV-CANCEL-CLAR (implement UX)
- INV-FIRST-TOKEN (capture + display + test)
- INV-TOOL-TRACE (stub + test)
- INV-GOV-ADR (add ADR for warning frame format)
- INV-CONFIG-BIDIR (reasoning ratio threshold test after config migration)

## Immediate Action Plan (Recommended Order)
1. Add debug instrumentation & sanitation guard (mitigate observed reasoning leak).
2. Implement contract tests for ratio & cap badges (lock current UI behavior).
3. Implement cancelled state UX (frontend changes + ensure existing cancellation metrics).
4. Add first_token_latency capture in pipeline context (record t_first_token) → expose via usage frame → update UI.
5. Implement tool trace stub UI + contract test.
6. Draft ADR for SSE warning frame + add test verifying warning event on ModelPassportMismatch.
7. Migrate reasoning ratio threshold to config key (update docs, add bi-directional config test 13k, update `.instructions.md`).

## Testing Requirements
Each new UI feature / invariant must include:
- Unit/contract test (UI or API) verifying presence/absence conditions.
- Metrics snapshot or assertion if new metric added.
- Negative path test (e.g., no CAP badge if cap_applied=false).

## Governance & Documentation
- Every new public field/event: update ADR or add new; update `.instructions.md` changed files list.
- Add to `docs/changelog/` with date + summary + invariants impacted.

## Definition of Done For Upcoming Tasks
- Cancelled UX: After user abort, final assistant message shows a `CANCELLED` badge (or icon), spinner removed within <300ms, usage event still emitted.
- first_token_latency: Usage event contains `first_token_latency_ms` (int), UI displays; contract test asserts numeric field.
- Tool trace stub: On zero tool events, dedicated component with text `No tool calls` appears in dev mode.
- Ratio & CAP tests: CI failing if badge appears outside threshold or appears without cap conditions.
- Warning frame ADR: Document fields (event: warning, payload.event, field, passport_value, config_value) + test.

## Expectations for New Assistant
- Read all referenced files before coding.
- Confirm invariants & priorities.
- Start with instrumentation if leak unresolved; otherwise contract tests.
- Always update `.instructions.md` and changelog for any public behavior.
- No silent threshold constants: all thresholds from config or documented fallback pending config migration.

Proceed by acknowledging these steps, then begin with Task 1 (instrumentation) unless instructed otherwise.
