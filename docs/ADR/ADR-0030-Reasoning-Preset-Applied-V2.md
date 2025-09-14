# ADR-0030: ReasoningPresetApplied Event V2

## Status
Accepted (2025-09-09)

## Context
Initial `ReasoningPresetApplied` (v1) emitted only the chosen preset name in field `mode` plus optional temperature/top_p. There was no explicit signal whether user overrides subsequently modified sampling parameters derived from the preset. Observability and governance (tracking drift from standard reasoning profiles) require distinguishing baseline vs overridden applications and listing which fields were changed.

## Decision
Introduce version 2 of the event payload:

Fields:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| request_id | str | yes | Generation (or agent op) request id |
| preset | str | yes | Name of reasoning preset requested (e.g. low, medium, high) |
| mode | str (enum) | yes | baseline | overridden |
| temperature | float | no | Final effective temperature after overrides |
| top_p | float | no | Final effective top_p after overrides |
| overridden_fields | list[str] | no | Which preset fields were changed by user overrides |

`mode=baseline` when no user sampling overrides affected preset-provided keys. `mode=overridden` when at least one preset-provided key differs in the final merged sampling. The original v1 field semantics (mode carrying preset name) are replaced by the new `preset` field; version number increments in Events.md.

## Rationale
Separating `preset` from override status avoids overloading a single field and supports future extensions (e.g. policy allowing only baseline usage for certain tenants). Listing `overridden_fields` provides granular audit without requiring reconstructing diffs externally.

## Alternatives Considered
1. Keep v1 and add boolean `overridden`: simpler but less expressive and would still misuse `mode` as preset.
2. Emit separate `ReasoningPresetOverridden` event: increases event volume and ordering race potential; rejected.

## Backward Compatibility
Tests only asserted presence of the event. Existing consumers expecting field `mode` holding a preset name must adapt: they should read `preset` for the preset and treat `mode` as override status when `v==2` (implicitly by Version column in Events.md). No rename of the event itself keeps subscription filters stable.

## Metrics Impact
Downstream aggregation (frequency of each preset) should group by `preset`; override rate by counting `mode=overridden` ratio per `preset`.

## Implementation Notes
Emission deferred until after user overrides are merged to compute overridden fields. Agent ops (judge/plan) always baseline (no user overrides) so emit `mode=baseline` with empty overridden_fields.

## Consequences
Enables governance dashboards: baseline usage %, top overridden fields distribution.

## Follow-up
Add sampling `mode=custom` tag (B8/B9) separately in GenerationStarted.sampling.

## References
ADR-0012 (GenerationResult), ADR-0028 (Pipeline Finalize Extraction), original Events.md entry.
