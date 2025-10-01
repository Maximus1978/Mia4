# Changelog 2025-09-19: Harmony Fused Marker & Duplicate Final Remediation

## Summary

Implemented backend sanitation for fused `assistantfinal` prefixes and duplicate final message suppression. Added leak metrics reasons (`fused_marker_prefix`, `duplicate_final`), new event `ReasoningSuppressedOrNone`, UI reasoning `(none)` state, SSE contract & UI tests, and ADR addendum.

## Details

- Backend: strip up to 3 leading fused prefixes; collapse exact doubled final (len>=8 & halves equal).
- Metrics: `reasoning_leak_total{reason}` extended; new `reasoning_none_total{reason}`.
- Event: `ReasoningSuppressedOrNone` emits when zero reasoning tokens.
- UI: removed '(waiting...)' placeholder; show `(none)` or toggle after first token; temporary defensive fused scrub.
- Tests: core sanitation unit tests; API SSE guard; UI contract markdown.
- Docs: ADR addendum + invariant extension (INV-CH-ISO now forbids fused residues).

## Risks & Mitigations

- False duplicate collapse: length threshold + exact half check.
- Legitimate leading phrase removal: pattern restricted to fused concatenation only.
- Over-sanitization concealment: metrics + debug hash diff ensure visibility.

## Follow-ups

- Remove client scrub after stable 48h metric window (<1 fused per 10k gens).
- Optional perf probe extension for sanitation overhead.
