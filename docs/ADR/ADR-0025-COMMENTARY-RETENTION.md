# ADR-0025: Commentary Retention Policy

## Status
Draft (2025-09-03)

## Context
`commentary` channel may contain explanations or contextual side notes. We must control retention (privacy, log size) and still gather metrics.

## Decision (Proposed)
Introduce config key `commentary_retention.mode` with enum:
- `metrics_only` (default): do not store commentary text; only count tokens
- `store_ephemeral`: keep in-memory until finalize then drop
- `store_persist`: persist alongside final (future, requires PII review)

Current implementation: metrics_only only; others raise NotImplemented until follow-up.

## Rationale
Start safest (no storage) while allowing future expansion without breaking contract.

## Metrics
- `commentary_tokens_total{model}` already implemented
- Future: `commentary_retention_mode_total{mode}` increment on session start

## Alternatives
Immediate persistence – rejected for privacy.

## Migration
Unknown keys rejected by config tests; add to Config-Registry when modes implemented.

## Next Steps
1. Implement mode validation & event redaction logic
2. Update tests for each mode
3. Promote ADR to Accepted

## References
Harmony commentary channel spec
