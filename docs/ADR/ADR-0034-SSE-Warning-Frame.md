# ADR-0034: SSE Warning Frame Format

Date: 2025-09-18
Status: Accepted
Author: MIA4 Team

## Context

The generation SSE stream already includes a transient warning toast in the UI for model passport vs runtime config mismatches (e.g., `max_output_tokens`). Today this is emitted ad-hoc in the `/generate` route via a JSON payload under an `event: warning` SSE frame. The format was not previously codified by an ADR, creating risk of silent contract drift and untested consumer assumptions.

Invariants to uphold:

- Warnings are non-fatal and must not alter token sequencing.
- Multiple warning frames MAY occur; clients should treat them idempotently keyed by `(event, field, request_id)`.
- Warning payloads must never contain model reasoning or partial deltas.
- Unknown keys are ignored by clients (forward compatibility).

## Decision

Standardize an SSE frame with:

- SSE event name: `warning`
- Data: JSON object containing common envelope fields plus a `event` discriminator.

### Envelope Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event` | string | Yes | Warning type discriminator. Current: `ModelPassportMismatch`. |
| `request_id` | string | Yes | Correlates with active generation request. |
| `model_id` | string | Yes | Model referenced by the generation. |
| `field` | string | Yes (for current event) | Name of the mismatched capability / limit. |
| `passport_value` | number | Yes (for mismatch) | Value from model passport. |
| `config_value` | number | Yes (for mismatch) | Value from active config. |
| `ts` | number | Optional | Epoch milliseconds when frame emitted (future). |

Additional warning types MUST document their required supplemental keys via changelog + test before merging.

### Emission Rules

- Emitted once per mismatched field per request (best-effort; duplication accepted but discouraged).
- Emitted before first token to maximize UX clarity; if discovered later still allowed.
- Emission failures are swallowed (best-effort observability, no user-facing error).

### Client Handling

- UI displays ephemeral toast (5s) summarizing mismatch.
- No persistence to chat history.
- Additional UI components MAY subscribe for analytics but must remain read-only.

## Alternatives Considered

1. Fold into usage frame: rejected (mixes orthogonal concerns; complicates caching of usage semantics).
2. Embed inside a commentary channel: rejected (commentary retention modes could suppress warnings; violates retention privacy contract).
3. Introduce a generic `meta` frame: postponed; `warning` is sufficiently scoped and low-risk now.

## Consequences

- Requires an explicit API contract test verifying shape and presence for a forced mismatch.
- Future warning types require ADR addendum or changelog entry referencing this ADR number.

## Test Plan

- Add `tests/api/test_warning_frame_passport_mismatch.py` forcing a mismatch by temporarily overriding config or injecting a synthetic passport limit.
- Assertions:
  - At least one `event: warning` frame.
  - JSON decodes with `event == 'ModelPassportMismatch'` and required numeric fields.
  - No token / final frames contain the warning payload (channel isolation preserved).

## Metrics / Observability

- (Future) Consider `warning_frames_total{event=...}` counter if operational monitoring shows need. Deferred to avoid metric noise (P2 backlog).

## Rollout

- Immediate: merge ADR + test.
- UI already consumes; no UI change required beyond ensuring no regressions.

## References

- INV-FIRST-TOKEN, INV-CH-ISO (ensure separation maintained)
- Previous related ADRs: Harmony Channel Separation v2 (ADR-0013i), Tool Calling Scope, Metrics Snapshot Legacy Compatibility.
