# 2025-09-18 Perf Panel Badge Tests (Placeholder)

Status: In-Progress

## Summary

Added placeholder Vitest spec `perf_panel_badges.spec.tsx` outlining contract scenarios for:

- Reasoning ratio alert badge (ALERT) threshold behaviour.
- CAP badge visibility when `cap_applied` true and effective_max_tokens available.
- CANCELLED badge visibility when `wasCancelled` is true.
- `first_token` latency display format (e.g., `first_token: 123 ms`).

## Rationale

Provides a scaffold ensuring upcoming implementation aligns with invariants: INV-RATIO-VIS, INV-CAP-UX, INV-CANCEL-CLAR, INV-FIRST-TOKEN.

## Next Steps

- Implement test mounting `PerfPanel` with varying props.
- Add negative assertions (badge absent below threshold / when flags false).
- Ensure stable data-testid attributes if needed (consider adding for ratio, cancel, cap badges).
- Once finalized, update this changelog entry to Shipped.

## Risks

Low. Placeholder only; no runtime impact.
