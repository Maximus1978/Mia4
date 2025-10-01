# Changelog: 2025-09-18 Perf Panel Enhancements & Cancellation UX

## Summary

Implemented UI and backend enhancements covering cancellation clarity and performance visibility:

- Added `first_token_latency_ms` capture on first streamed final-channel token; surfaced via `usage` and `final` SSE frames and documented in `docs/API.md`.
- Updated React perf panel to display `first_token: <N> ms` alongside overall latency, decode_tps, token counts, context usage, reasoning ratio, CAP progress.
- Introduced CANCELLED badge (distinct styling) when generation aborts mid-stream (spinner now removed promptly).
- Extended `UsageEvent` interface with new field while preserving backward compatibility (optional property).
- Added placeholder UI contract specs for: first token latency, cancelled state, ratio badge, CAP badge (real automated tests pending test harness).

## Details

Backend:

- `src/mia4/api/routes/generate.py`: records timestamp delta on first `delta` event, observes `generation_first_token_latency_ms` metric, injects field into `usage` & `final` payloads.
- Metrics: histogram `generation_first_token_latency_ms` already defined; now populated.

Frontend:

- `chatgpt-design-app/src/api.ts`: `UsageEvent` adds optional `first_token_latency_ms`.
- `ChatWindow.tsx`: perf panel rendering logic updated; null-safe guards when `lastUsage` missing (cancelled early). Added conditional CANCELLED badge.
- Improved JSX structure around CAP progress bar and reasoning ratio block (previous patch cleanup).

Docs & Specs:

- `docs/API.md`: usage frame schema updated with `first_token_latency_ms`.
- Added placeholder specs: `tests/ui/test_first_token_latency_placeholder.md`, `tests/ui/test_cancelled_state_placeholder.md` (plus earlier ratio & cap placeholders).
- `.instructions.md`: Execution Plan items 6b, 11c, 11d marked completed; INV-FIRST-TOKEN updated (tests pending).

## Invariants Impact

- Advances INV-CANCEL-CLAR (UX implemented; test pending).
- Advances INV-FIRST-TOKEN (data + UI present; contract test outstanding).
- No regression risk to INV-CH-ISO (purely additive fields/UI markers).

## Testing

- Manual verification of SSE payload structure (inspection / code review level). Automated API test for latency remains to be authored (11e).
- Existing sanitation and channel isolation tests unaffected.
- Placeholders ensure intent captured pending UI test harness.

## Risks / Mitigations

- Risk: Late first token on heavy model load may inflate latency metrics; acceptable (reflects real UX). Future: differentiate cold vs warm via model load event correlation.
- Risk: UI layout crowding; mitigated by concise label `first_token` and ordering before throughput.

## Follow-Up (P1)

1. Implement contract tests: ratio badge, CAP badge, cancelled badge, first_token_latency.
2. Tool trace stub ("No tool calls") + test.
3. ADR + test for warning frame (ModelPassportMismatch).
4. Config migration for reasoning ratio threshold + bi-directional test.
5. Remove legacy `reasoningSanitization.ts` after confirming zero leaks.

## Metrics / Observability

- Expect new observations in `generation_first_token_latency_ms` histogram on every generation with at least one token.
- Cancellation path still emits usage frame enabling latency + partial token counts for analysis.

## Verification Steps (Manual)

1. Start backend & UI; send prompt; observe perf panel shows both `latency:` and `first_token:` values.
2. Cancel mid-stream; observe CANCELLED badge and absence of spinner.
3. Inspect browser network stream to confirm `first_token_latency_ms` present in usage event JSON.

--- End of entry --
