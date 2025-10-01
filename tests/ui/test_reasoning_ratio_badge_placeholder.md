# Reasoning Ratio Badge Contract Test (Placeholder)

This placeholder documents the intended automated UI contract test ensuring:

- ALERT badge (`.badge.ratio-alert`) is rendered only when `reasoning_ratio >= threshold`.
- Threshold source: config key (post-migration) or temporary localStorage key `mia.reasoning_ratio.threshold` (current).
- No badge when `reasoning_ratio < threshold` or field absent.
- Ratio text shows `reasoning: <reasoning_tokens>/<final_tokens> (<N>%)` where `<N>` equals `Math.round(ratio*100)` (currently `(rr * 100).toFixed(0)` in component).

Implementation Plan:
1. Introduce headless DOM test harness (vitest + jsdom) aligned with existing build tooling.
2. Provide injectable stream/mock: wrap `ChatWindow` with a context or prop allowing injection of a synthetic `lastUsage` object.
3. Emit two scenarios:
   - Case A: ratio exactly threshold (e.g., ratio=0.35, threshold=0.35) → badge visible.
   - Case B: ratio just below threshold (ratio=0.34, threshold=0.35) → badge absent.
4. Negative path: omit `reasoning_ratio` → badge absent.
5. Accessibility: ensure badge has `title` attribute (currently provided: `ALERT` via inner strong). If not, add for a11y.

Metrics Linkage:
- Supports invariant INV-RATIO-VIS.

Status: Pending harness. Will be converted to `test_reasoning_ratio_badge.ts` once frontend test stack dependencies (preact/testing-library) are added to `package.json`.

Blocking Items:
- Add dev-friendly injection point for `lastUsage` (could export a small helper component in test-only build).
- Add `vitest` / `@testing-library/preact` dev dependencies.

Tracking: INV-RATIO-VIS.
Owner: Harmony P1 phase.