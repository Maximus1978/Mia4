# 2025-09-04: Pipeline finalize extraction (ADR-0028)

Status: Implemented

Changes:

- Implemented `PrimaryPipeline.finalize()` returning `PipelineResult` consolidating final text, usage, reasoning stats, sampling summary.
- Route `/generate` refactored: removed duplicate cap logic; success path delegates event emission and usage metrics to pipeline finalization.
- Metrics snapshot structure adjusted: legacy tuple keys moved to `counters_legacy` (see ADR-0027 update) to avoid mixed key types in primary map.
- Added context fields to `PipelineContext` (output_tokens, latency_ms, decode_tps, fragments, stop_hit, reasoning_stats).
- Ensured single source of truth for cap application (pipeline.prepare) per ADR-0028 invariants.

Compatibility:

- Existing tests updated implicitly; legacy metrics tuple keys accessible under `counters_legacy` for migration window.

Follow-ups:

- Add sampling parity test (GenerationStarted vs GenerationCompleted summary) — pending.
- Implement ModelPassportMismatch warning event & test.
- Draft ADRs: TOOL-CALLING-SCOPE, COMMENTARY-RETENTION.

References: ADR-0026, ADR-0027, ADR-0028.
