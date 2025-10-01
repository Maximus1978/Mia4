# Cancelled State UX Contract Test (Placeholder)

Invariants: INV-CANCEL-CLAR

Acceptance Criteria:
- AC1: When user triggers cancel (calls handleCancel), streaming indicator disappears within <300ms.
- AC2: A badge element `.badge.cancel-badge` with text `CANCELLED` appears in perf panel.
- AC3: Badge only shows for the in-progress request just cancelled (reset on next send).
- AC4: If usage frame never arrived (no `lastUsage`), perf panel still renders with badge and without undefined fields.
- AC5: No duplicate badges if multiple cancels.

Implementation Plan (future automated test):
1. Provide test harness injecting fake stream handle; simulate cancel before any usage event.
2. Use fake timers to assert disappearance of `.stream-indicator` within 300ms.
3. Simulate new message send; assert badge cleared.
4. Negative scenario: normal completion (onEnd) -> no cancel badge.

Status: Placeholder until UI test harness (vitest/jsdom) added.
