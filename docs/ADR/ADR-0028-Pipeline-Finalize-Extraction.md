# ADR-0028: Pipeline Finalize Extraction & `PipelineResult` Contract

Status: Proposed
Date: 2025-09-03
Authors: Core Team
Relates-To: ADR-0026 (Pipeline Separation), ADR-0027 (Metrics Legacy Compatibility)
Supersedes: —

## Context

After ADR-0026 only the `prepare()` phase was extracted into `PrimaryPipeline`. The HTTP route (`mia4.api.routes.generate`) still performs responsibilities that belong to the pipeline `finalize()` phase:

* Accumulating streamed token fragments into final text
* Stop sequence trimming & echo/system prompt stripping
* Reasoning stats & ratio alert emission
* Latency / throughput (first token + total) observation
* Emitting `GenerationCompleted`
* Constructing sampling & reasoning summaries (duplicating cap logic)
* Deriving & duplicating `cap_applied` (double derivation risk)

This causes:

* Contract drift risk between `GenerationStarted.sampling` and `GenerationCompleted.result_summary.sampling`
* Harder testability (finalization logic only reachable through HTTP SSE)
* Risk of inconsistent cap metrics (route vs pipeline)

## Decision

Move all finalization responsibilities into `GenerationPipeline.finalize()` and standardize the return value via a new `PipelineResult` dataclass.

### `PipelineResult` Fields

| Field | Type | Description |
|-------|------|-------------|
| `final_text` | str | Post-processed assistant text (after echo & stop trimming) |
| `usage` | dict | Usage & performance snapshot (`prompt_tokens`, `output_tokens`, `latency_ms`, `decode_tps`, plus `reasoning_*` if present, `adapter`, `cap_applied`, `effective_max_tokens`) |
| `reasoning_stats` | dict | Reasoning token statistics (`reasoning_tokens`, `final_tokens`, `reasoning_ratio`, `adapter`) or None |
| `sampling_summary` | dict | `{requested_max_tokens, effective_max_tokens, cap_applied, cap_source}` derived from `ctx.sampling` (single source of truth) |
| `stop_reason` | str | Stop reason enum (`stop_sequence` \| None) |

No new public fields are exposed beyond what route already serialized; consolidation only.

### Event Consistency Rules

* `GenerationCompleted.result_summary.sampling` mirrors exactly `GenerationStarted.sampling` keys & values (except for immutable ordering differences).
* `cap_applied` is derived once inside `prepare()` and reused in `finalize()`; route must not re-derive.
* Ratio alert (`reasoning_ratio_alert_total`) emission remains in finalize when reasoning stats known.

### Route Simplification

Route orchestration sequence becomes:

1. `ctx = pipeline.prepare(...)`
2. Stream: for each adapter event from `pipeline.stream(ctx)` → convert to SSE (analysis/commentary/delta/final-metadata interim)
3. After stream exhaustion: `result = pipeline.finalize(ctx)`
4. Emit SSE blocks: `usage`, optional `reasoning`, `final`, `end`

Abort / timeout still handled by route (emitting `GenerationCancelled`).

## Alternatives Considered

* Keep finalize in route: retains duplication & complexity.
* Introduce callback hooks from route into pipeline: unnecessary indirection for single primary pipeline.

## Consequences

* Cleaner boundary; future pipelines (lightweight, RAG) can override finalize with custom trimming or summaries.
* Tests can fabricate a `PipelineContext` and call `finalize()` directly (unit coverage for sampling synchronization).
* Slight refactor churn in `generate.py` (reduced lines & duplication removed).

## Migration & Compatibility

* No change in SSE schema fields or event names.
* Legacy metrics dual-key snapshot unaffected (ADR-0027 stays valid).
* Remove route-level cap recomputation; rely solely on `ctx.sampling`.

## Testing Additions

1. Assert `GenerationStarted.sampling == GenerationCompleted.result_summary.sampling` for overlapping keys.
2. Assert `cap_applied` only computed in `prepare()` (no second metric increment beyond the one from prepare, except legacy safe guard kept inside finalize for idempotency — counter design tolerates duplicate increments but test checks absence of route recompute logic).

## Open Items (Subsequent ADRs)

* ModelPassportMismatch event & metric (separate ADR not required – small internal event) but tracked in execution plan.
* Commentary retention policy (ADR-COMMENTARY-RETENTION) – governs storage/sanitization.
* Tool calling scope (ADR-TOOL-CALLING-SCOPE).

## Status & Next Steps

Implement pipeline `finalize()` now, refactor route, add tests, then mark this ADR Accepted in changelog once green.

## Changelog

To be added upon acceptance: "2025-09-03 finalize extraction (ADR-0028) consolidates sampling & completion logic inside pipeline".
