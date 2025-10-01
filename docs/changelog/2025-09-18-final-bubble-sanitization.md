# 2025-09-18 Final Bubble Sanitization & SSE Final Event

Status: added

## Summary

Introduced dedicated `event: final` SSE frame carrying authoritative sanitized final text and reasoning stats. UI updated to:

- Replace last AI message content with `final.text` on receipt.
- Sanitize any residual service markers defensively in streaming token deltas.

## Rationale

Previously UI assembled visible answer by concatenating streamed `token` deltas. In rare sanitation scenarios (adapter scrub of service markers after finalize) the concatenated client buffer could transiently contain `<|...|>` markers or mismatched text relative to backend metrics. Providing an explicit final frame ensures Single Source Of Truth alignment (SSOT) between backend post‑processing and UI render.

## Changes

- Backend: emit `event: final` with sanitized `text` and stats.
- Frontend: `ChatWindow` now listens for `onFinal` callback and replaces buffered answer.
- Defensive client regex removal of residual service markers in `onToken`.
- New core test `test_no_service_markers_in_stream.py` guarding against leakage.
- API docs updated with `event: final` schema.

## Invariants Reinforced

- INV-CH-ISO: final UI text sourced exclusively from sanitized final payload.
- INV-RATIONALE-SSOT: Single definitive final text authority (no divergence).

## Follow-ups

- Remove legacy sanitization layer after soak (see task list).
- Add HTML snapshot regression test (planned P2) ensuring absence of service markers in rendered DOM.
