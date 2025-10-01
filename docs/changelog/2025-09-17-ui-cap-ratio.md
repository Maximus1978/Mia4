# Changelog: 2025-09-17 UI Ratio Alert & CAP Progress

## Summary
Implemented two P1 UI deliverables: reasoning ratio alert badge (5b) and cap progress bar + CAP badge (7e). Updated `UsageEvent` interface to include `cap_applied` and `effective_max_tokens`. Added placeholder contract test specs for CAP badge. Marked tasks complete in `.instructions.md` and captured remaining P1 obligations (contract tests, cancelled UX, first_token_latency, tool trace stub, SSE warning ADR).

## Details
- ChatWindow: added reasoning ratio badge conditional on configurable threshold (localStorage key `mia.reasoning_ratio.threshold`, fallback 0.35).
- ChatWindow: added cap progress wrapper with linear progress bar and CAP badge when `cap_applied=true`.
- Styles: new CSS classes (`cap-progress-*`, `.badge.cap-badge`, `.reasoning-ratio.over`).
- API TypeScript: extended `UsageEvent` with optional `cap_applied`, `effective_max_tokens`.
- Added NPM `dev` script for consistency (`npm run dev`).
- Placeholder test doc `tests/ui/test_cap_badge_placeholder.md` describing contract criteria.

## Metrics / Invariants Impact
- Supports INV-RATIO-VIS (visual portion complete; contract test pending).
- Supports INV-CAP-UX (visual portion complete; contract test pending).
- No backend metric schema changes; only UI consumption.

## Risks / Follow-ups
- Missing contract tests could allow silent regressions (priority next).
- Observed potential reasoning leak under large max_output_tokens scenario; requires debug instrumentation (planned) and sanitation guard enhancements.
- Need to ensure ratio threshold moves to config + bi-directional test (13k) before marking invariant fully satisfied.

## Next (P1) Targets
1. Contract tests (ratio badge, CAP badge).
2. Cancelled state UX (6b).
3. first_token_latency capture + UI (11c–11e).
4. Tool calls stub (8d/8e).
5. ADR + test for SSE warning frame (13j).

## Verification
- Frontend build succeeded (`vite build`).
- Core backend test suite: 110 passed, 8 skipped, 0 failures.
