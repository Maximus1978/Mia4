# ADR-0013i Addendum: Harmony Fused Marker & Duplicate Final Remediation

Date: 2025-09-19
Status: Accepted
Supersedes / Extends: ADR-0013i (Harmony Channel Separation v2)
Authors: MIA4 Team

## Context

Post adoption of Harmony Channel Separation v2 we observed residual textual artifacts leaking into `final` user-visible output:

1. Fused service marker prefixes: `assistantfinal` / `assistant final` (concatenation of role + channel markers) at the very start of final text.
2. Duplicate final payload: entire final answer repeated twice in a single final frame (e.g. `Answer...Answer...`).
3. Misleading reasoning placeholder `(waiting...)` shown after completion when no reasoning tokens were ever produced.

These issues violated invariant INV-CH-ISO (no mixing / textual residue of service markers in final channel) and reduced UX clarity.

## Decision

Implement backend sanitation + detection with explicit metrics & tests and align UI UX semantics.

### Backend Changes

- Strip up to 3 leading fused prefixes matching regex `^(assistant\s*final){1,3}` before final emission.
- Suppress exact doubled final text when length even, halves equal, and half length >= 8 (to avoid collapsing short tokens like `OKOK`).
- Emit `reasoning_leak_total{reason="fused_marker_prefix"}` and/or `{reason="duplicate_final"}` when applied.
- Emit new event `ReasoningSuppressedOrNone` when `reasoning_tokens == 0` (reasons: `no-analysis-channel`, `drop_history`, or both).
- Re-tokenize sanitized final preserving accuracy of stats (counts reflect visible text).

### UI Changes

- Remove pre-token placeholder; reasoning panel appears only when first reasoning token arrives or after completion (showing `(none)` if absent).
- Temporary defensive client scrub for fused prefix (to be removed after confidence window) using same regex.

### Metrics / Observability

- New metric labels for `reasoning_leak_total`: `fused_marker_prefix`, `duplicate_final`.
- New counter `fused_marker_sanitizations_total{kind}` to track prefix/residue sanitation activations.
- New counter `reasoning_none_total{reason}` via `ReasoningSuppressedOrNone` event.
- Existing anomaly & sanitation pathways unchanged (service markers still scrubbed; reasons `service_marker_in_final`, `finalize_sanitize`).

### Invariants Updated

- INV-CH-ISO extended: prohibits fused concatenations of service markers (not only raw `<|...|>` forms).
- INV-LEAK-METRICS: now explicitly includes fused prefix & duplicate final as leak categories.

## Alternatives Considered

1. Pure UI fix (reject) — would mask server contract breach and hide telemetry.
2. Over-aggressive regex removing any `assistant` prefix (reject) — risk of legitimate content loss.
3. Hash-based de-dup over rolling window (reject for complexity) — simple exact half comparison sufficient.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| False positive duplicate collapse on structured outputs | Length >=8 + exact half rule limits cases |
| Legitimate text starting with "assistant final" removed | Pattern only matches fused *repetition* (joined words) at leading edge |
| Over-sanitization hides upstream regression | Metrics increment with explicit reasons; debug diff hash logged when debug mode on |
| Client scrub lingers beyond necessity | TODO: create follow-up task to remove once backend proven stable |

## Test Matrix

| Test | Scenario | Expected |
|------|----------|----------|
| `test_harmony_fused_sanitation.py::test_fused_prefix_single` | single fused | prefix removed + metric |
| `...::test_fused_prefix_multiple` | multiple fused | all stripped + metric |
| `...::test_duplicate_final_suppression` | doubled final | collapsed + metric |
| `...::test_short_duplicate_not_suppressed` | short repeat | unchanged, no metric required |
| `api/test_sse_no_fused_prefix.py` | SSE stream final | no fused prefix / markers |
| UI `test_reasoning_none_label.md` | no reasoning tokens | header shows `(none)` |

## Rollout Plan

1. Deploy backend sanitation + metrics.
2. Ship UI defensive scrub + `(none)` semantics.
3. Monitor `reasoning_leak_total{reason in [fused_marker_prefix, duplicate_final]}` goes to zero baseline after initial burn-in.
4. Remove client scrub (separate PR) once <1 event per 10k generations for 48h.

## Follow-ups

- Remove temporary client scrub (create ticket).
- Add perf probe to ensure sanitation logic does not regress decode TPS (currently lightweight O(n) on small final strings).
- Extend SSE contract tests to assert absence of duplicate final halves explicitly (optional if metrics stable).

## References

- ADR-0013i (Channel Separation v2)
- Changelog entry (2025-09-19) — to be added
- `.instructions.md` remediation block R1–R12

