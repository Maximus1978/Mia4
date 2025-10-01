# 2025-09-18 Final Bubble Idealization

Status: Shipped

## Summary

Refined final message sanitation pipeline after initial P0 fix:

- Centralized service marker regex as `SERVICE_MARKER_RE` within `HarmonyChannelAdapter` (single source of truth, no ad-hoc patterns).
- Added API contract test `test_generate_final_frame_sanitized.py` verifying `event: final` frame contains no `<|...|>` service/channel markers and includes sanitized `final_text`.
- Shortened debug logging line length to satisfy lint and improve clarity.

## Rationale

Prevents drift between adapter sanitation and downstream UI/client assumptions, reinforcing INV-CH-ISO (no service markers or reasoning tokens in final_text). Ensures explicit guard at API layer before UI rendering.

## Tests

- `tests/api/test_generate_final_frame_sanitized.py` (new) — asserts absence of markers in final frame and presence of `final_text` field.
- Existing core isolation tests remain green (no changes required).

## Metrics / Observability Impact

No new metrics added. Existing leak metrics still fire if upstream anomalies occur prior to sanitize.

## Follow-ups

- Remove legacy client-side `reasoningSanitization` utility once confidence window (≥1 week) passes and UI contract tests land.
- Add UI contract test ensuring final bubble renders exactly `final_text` string without transformations.

## Risks

Low — regex centralization reduces divergence risk; sanitation semantics unchanged.
